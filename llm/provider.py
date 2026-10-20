"""Local-only Ollama adapter. Bounded work, explicit fallback, no automatic pulls."""
import contextlib
import json
import http.client
import io
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


class LLMResult:
    def __init__(self, available, text, error=None, metadata=None):
        self.available, self.text, self.error = available, text, error
        self.metadata = metadata or {}


class OllamaProvider:
    def __init__(self, settings, logger=None):
        self.settings, self.logger = settings, logger
        self.call_count = 0
        self._lock = threading.RLock()
        self._local = threading.local()
        self._cooldown_until = 0
        self.last_metadata = {}
        self._connection_lock = threading.Lock()
        self._active_connection = None
        self._cancel_requested = threading.Event()
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @contextlib.contextmanager
    def turn_budget(self, seconds=None):
        previous = getattr(self._local, "deadline", None)
        self._local.deadline = time.monotonic() + float(seconds or self.settings.get("llmTurnBudgetSeconds", 24))
        try:
            yield
        finally:
            self._local.deadline = previous

    def _base(self):
        parsed = urllib.parse.urlsplit(str(self.settings.get("ollamaUrl", "http://127.0.0.1:11434/api/generate")))
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Ollama deve usar HTTP em loopback local, sem credenciais.")
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))

    def _json(self, path, timeout, payload=None):
        base=self._base()
        parsed=urllib.parse.urlsplit(base)
        connection=http.client.HTTPConnection(parsed.hostname,parsed.port or 80,timeout=max(.05,timeout))
        try:
            connection.connect()
            if payload is not None:
                with self._connection_lock:
                    self._active_connection=connection
                if self._cancel_requested.is_set():
                    raise OSError('Interrompido pelo usuário')
            connection.request('POST' if payload is not None else 'GET',path,
                body=json.dumps(payload).encode() if payload is not None else None,
                headers={'Content-Type':'application/json'})
            response=connection.getresponse()
            raw=response.read(2_000_001)
            if response.status>=400:
                raise urllib.error.HTTPError(base+path,response.status,response.reason,response.headers,io.BytesIO(raw))
        finally:
            with self._connection_lock:
                if self._active_connection is connection:
                    self._active_connection=None
            connection.close()
        if len(raw) > 2_000_000:
            raise ValueError("Resposta Ollama excede limite local")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Resposta Ollama inválida")
        return data

    def cancel_current(self):
        self._cancel_requested.set()
        with self._connection_lock:
            connection=self._active_connection
            if connection is not None and connection.sock is not None:
                try:
                    connection.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                return True
        return False

    def generate(self, prompt, timeout_seconds=None, response_format=None, messages=None, model_override=None, tools=None):
        self.call_count += 1
        if not self.settings.get("useLLM", True):
            return LLMResult(False, "", "LLM desativada")
        if time.monotonic() < self._cooldown_until:
            return LLMResult(False, "", "Ollama em intervalo de recuperação")
        timeout = float(timeout_seconds if timeout_seconds is not None else self.settings.get("llmTimeoutSeconds", 20))
        turn_deadline = getattr(self._local, "deadline", None) or float("inf")
        deadline = min(time.monotonic() + timeout, turn_deadline)
        if not self._lock.acquire(timeout=max(0, deadline - time.monotonic())):
            return LLMResult(False, "", "LLM ocupada; orçamento esgotado")
        started = time.monotonic()
        try:
            self._cancel_requested.clear()
            model = str(model_override or self.settings.get("ollamaModel", "qwen2.5:3b"))
            fallbacks = self.settings.get("ollamaFallbackModels", [])
            fallbacks = fallbacks if isinstance(fallbacks, list) else []
            candidates = list(dict.fromkeys([model] + [str(x) for x in fallbacks]))[:2]
            for candidate in candidates:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Orçamento LLM esgotado")
                payload = {"model": candidate, "prompt": str(prompt), "stream": False,
                    "think": False, "keep_alive": self.settings.get("ollamaKeepAlive", "5m"),
                    "options": {"num_ctx": int(self.settings.get("ollamaNumCtx", 4096)),
                        "num_predict": int(self.settings.get("ollamaNumPredict", 384)),
                        "temperature": .1 if response_format else .6}}
                endpoint = "/api/chat" if self.settings.get("ollamaApi", "chat") == "chat" else "/api/generate"
                if endpoint == "/api/chat":
                    payload["messages"] = messages or [{"role": "user", "content": payload["prompt"]}]
                    payload.pop("prompt")
                if response_format:
                    payload["format"] = response_format
                if tools:
                    if endpoint != "/api/chat":
                        raise ValueError("Ferramentas exigem ollamaApi=chat")
                    payload["tools"] = tools
                    payload["options"]["temperature"] = .1
                try:
                    data = self._json(endpoint, remaining, payload)
                except urllib.error.HTTPError as error:
                    detail = error.read(8192).decode("utf-8", errors="replace")
                    error.close()
                    unavailable = error.code == 404 or (error.code in {400, 500} and any(
                        marker in detail.lower() for marker in ("not supported", "requires more system memory", "not enough memory", "unknown model architecture")
                    ))
                    if unavailable and candidate != candidates[-1]:
                        continue
                    raise ValueError(f"Ollama HTTP {error.code}: {detail[:500]}") from error
                message = data.get("message") if isinstance(data.get("message"), dict) else {}
                text = str(message.get("content") or data.get("response") or "").strip()
                if data.get("error") or (not text and not message.get("tool_calls")):
                    raise ValueError(data.get("error") or "Ollama retornou resposta vazia")
                self.last_metadata = {"model": candidate, "fallback": candidate != model,
                    "elapsed_ms": round((time.monotonic()-started)*1000),
                    "eval_count": data.get("eval_count"), "eval_duration": data.get("eval_duration"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "load_duration": data.get("load_duration"), "finish_reason": data.get("done_reason", "stop")}
                if tools:
                    self.last_metadata["message"] = message
                return LLMResult(True, text, metadata=self.last_metadata)
            raise ValueError("Nenhum modelo disponível")
        except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException) as error:
            cancelled=self._cancel_requested.is_set()
            if not cancelled:
                self._cooldown_until = time.monotonic() + float(self.settings.get("ollamaRecoverySeconds", 15))
            if self.logger:
                self.logger.log("LLM_UNAVAILABLE", str(error))
            return LLMResult(False, "", 'Interrompido pelo usuário' if cancelled else str(error))
        finally:
            self._lock.release()

    def health_check(self):
        if not self.settings.get("useLLM", True):
            return {"available": False, "status": "desativada", "error": "useLLM=false"}
        try:
            data = self._json("/api/tags", 2)
            names = [item.get("name") for item in data.get("models", [])]
            fallbacks = self.settings.get("ollamaFallbackModels", [])
            selected = [self.settings.get("ollamaModel", "qwen2.5:3b")] + (fallbacks if isinstance(fallbacks, list) else [])
            installed = next((name for name in selected if name in names), None)
            return {"available": bool(installed), "status": "ativa" if installed else "modelo ausente",
                "model": installed, "models": names, "error": "" if installed else "Instale um modelo configurado com ollama pull"}
        except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException) as error:
            return {"available": False, "status": "inativa", "error": str(error)}
