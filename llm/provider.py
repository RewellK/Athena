import json
import urllib.error
import urllib.request


class LLMResult:

    def __init__(self, available, text, error=None):
        self.available = available
        self.text = text
        self.error = error


class OllamaProvider:

    def __init__(self, settings, logger=None):
        self.settings = settings
        self.logger = logger

    def generate(self, prompt, timeout_seconds=None):
        if not self.settings.get("useLLM", True):
            return LLMResult(False, "", "LLM desativada em config/settings.json")

        url = self.settings.get("ollamaUrl")
        model = self.settings.get("ollamaModel")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        timeout = timeout_seconds if timeout_seconds is not None else self.settings.get("llmTimeoutSeconds", 30)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                return LLMResult(True, data.get("response", "").strip())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
            if self.logger:
                self.logger.log("LLM_UNAVAILABLE", str(error))
            return LLMResult(False, "", str(error))


    def health_check(self):
        if not self.settings.get("useLLM", True):
            return {"available": False, "status": "desativada", "error": "useLLM=false"}
        url = str(self.settings.get("ollamaUrl") or "")
        base = url.split("/api/")[0] if "/api/" in url else url.rstrip("/")
        tags_url = base.rstrip("/") + "/api/tags"
        try:
            with urllib.request.urlopen(tags_url, timeout=2) as response:
                response.read()
                return {"available": True, "status": "ativa", "error": ""}
        except Exception as error:
            if self.logger:
                self.logger.log("LLM_HEALTH_UNAVAILABLE", str(error))
            return {"available": False, "status": "inativa", "error": str(error)}
