import json
import time


class IntentInterpreter:
    """Interprets conversational intent with a fast path and a compact LLM path.

    The fast path is deliberately small and only handles UX-critical generic
    conversational forms. It does not create knowledge, does not extract world
    structures and does not encode domains such as countries, people or objects.
    """

    VALID_INTENTS = {
        "greeting",
        "small_talk",
        "identity",
        "creator_query",
        "question_about_user",
        "capability",
        "self_status",
        "memory_query",
        "world_query",
        "reasoning",
        "learning",
        "agency",
        "system",
        "error_query",
        "technical_capability",
        "conversation",
        "unknown",
    }

    PRIORITY = [
        "error_query",
        "identity",
        "creator_query",
        "question_about_user",
        "self_status",
        "capability",
        "technical_capability",
        "memory_query",
        "world_query",
        "reasoning",
        "agency",
        "learning",
        "small_talk",
        "greeting",
        "conversation",
        "unknown",
    ]

    def __init__(self, llm_provider=None, identity=None, logger=None, settings=None):
        self.llm_provider = llm_provider
        self.identity = identity or {}
        self.logger = logger
        self.settings = settings

    def interpret(self, user_input, session_context=None, pending_state=None):
        started_at = time.perf_counter()
        fast = self._fast_path(user_input, pending_state)
        if fast and fast.get("confidence", 0) >= 0.88:
            fast["duration_ms"] = self._elapsed(started_at)
            return fast

        if self.settings and not self.settings.get("useLLM", True):
            fallback = fast or self._result("conversation", confidence=0.50, source="fast_path_only")
            fallback["duration_ms"] = self._elapsed(started_at)
            return fallback

        llm_result = self._llm_interpret(user_input, session_context, pending_state)
        if llm_result and llm_result.get("confidence", 0) >= 0.50:
            llm_result["duration_ms"] = self._elapsed(started_at)
            return llm_result

        fallback = fast or self._result("conversation", confidence=0.45, source="safe_fallback")
        fallback["duration_ms"] = self._elapsed(started_at)
        return fallback

    def _llm_interpret(self, user_input, session_context=None, pending_state=None):
        if not self.llm_provider:
            return None
        prompt = self._build_prompt(user_input, session_context, pending_state)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            parsed = self._parse_json(result.text)
            return self._normalize(parsed, "llm_intent_interpreter")
        except Exception as error:
            if self.logger:
                self.logger.log("INTENT_INTERPRETER_ERROR", str(error))
            return None

    def _build_prompt(self, user_input, session_context=None, pending_state=None):
        creator = self.identity.get("creator", "Rewell")
        athena_name = self.identity.get("name", "Athena")
        recent = session_context.summary(limit=6) if session_context else ""
        pending = pending_state or {}
        intents = ", ".join(self.PRIORITY)
        return f"""
Você é o interpretador de intenção conversacional da Athena.
Retorne SOMENTE JSON válido, sem markdown e sem explicações.
Não extraia conhecimento de mundo. Não crie entidades. Apenas classifique a intenção.

Identidade básica:
- Nome da entidade: {athena_name}
- Criador/usuário principal: {creator}

Prioridade: quando houver saudação + pergunta, classifique pela pergunta mais importante, não pela saudação.
Intenções permitidas: {intents}

Schema:
{{
  "intent": "string",
  "target": "string",
  "confidence": 0.0,
  "should_use_llm_response": true,
  "should_learn": false,
  "should_query_world_model": false,
  "should_query_self_model": false,
  "should_use_reasoning": false,
  "should_use_agency": false,
  "summary": "string",
  "structured_request": {{}}
}}

Diretrizes:
- identity: pergunta sobre quem é Athena.
- creator_query: pergunta sobre quem criou Athena.
- question_about_user: pergunta sobre {creator} ou sobre outra pessoa/entidade específica.
- capability: pergunta geral sobre o que Athena consegue fazer.
- technical_capability: pedido técnico sobre módulos/arquitetura.
- self_status: pergunta sobre estado operacional da Athena.
- learning: mensagem traz informação nova que provavelmente deve ser aprendida.
- world_query: pergunta sobre entidades, pessoas, objetos, relações, eventos ou estados conhecidos.
- error_query: pergunta sobre erro/falha/problema recente.
- system: pergunta operacional sobre voz, Git, configuração ou desktop.
- small_talk/greeting: conversa casual sem necessidade de aprendizado.

Estado pendente:
{json.dumps(pending, ensure_ascii=False)}

Contexto recente:
{recent}

Mensagem:
{user_input}
""".strip()

    def _fast_path(self, user_input, pending_state=None):
        text = str(user_input or "").strip()
        normalized = self._normalize_text(text)
        if not normalized:
            return self._result("conversation", confidence=0.50, source="fast_path")

        pending_type = (pending_state or {}).get("pending_type")
        if pending_type and pending_type != "none":
            approval = self._approval_route(normalized)
            if approval:
                return approval

        has_question = "?" in text or self._starts_with_any(normalized, [
            "quem", "qual", "quais", "quanto", "quantas", "como", "por que", "porque", "what", "who", "how", "why", "where", "cuando", "cuándo", "que", "qué"
        ])

        if self._is_error_query(normalized):
            return self._result("error_query", target="last_error", confidence=0.93, operation=self._error_operation(normalized), source="fast_path")

        if self._is_creator_query(normalized):
            return self._result("creator_query", target=self.identity.get("creator", "Rewell"), confidence=0.94, operation="creator", source="fast_path")

        if self._is_identity_query(normalized):
            return self._result("identity", target=self.identity.get("name", "Athena"), confidence=0.94, operation="describe_self", source="fast_path")

        if self._looks_like_small_talk(normalized):
            return self._result("small_talk", confidence=0.90, source="fast_path")

        if self._is_status_query(normalized):
            return self._result("self_status", confidence=0.91, operation="health", source="fast_path")

        if self._is_technical_capability_query(normalized):
            return self._result("technical_capability", confidence=0.90, operation="technical_modules", source="fast_path")

        if self._is_capability_query(normalized):
            return self._result("capability", confidence=0.90, operation="summary", source="fast_path")

        if self._is_system_query(normalized):
            subsystem, operation = self._system_operation(normalized)
            return self._result("system", confidence=0.86, operation=operation, target=subsystem, structured_request={"subsystem": subsystem, "operation": operation}, source="fast_path")

        target = self._generic_who_target(normalized)
        if target:
            creator = self._normalize_text(self.identity.get("creator", "Rewell"))
            athena = self._normalize_text(self.identity.get("name", "Athena"))
            if target == athena:
                return self._result("identity", target=self.identity.get("name", "Athena"), confidence=0.92, operation="describe_self", source="fast_path")
            if target == creator:
                return self._result("question_about_user", target=self.identity.get("creator", "Rewell"), confidence=0.90, operation="describe_target", source="fast_path")
            return self._result("world_query", target=target, confidence=0.72, operation="query_entity", structured_request={"operation": "query_entity", "target": target}, source="fast_path")

        if self._looks_like_greeting_only(normalized):
            return self._result("greeting", confidence=0.96, source="fast_path")

        if has_question:
            return self._result("conversation", confidence=0.55, should_use_llm_response=True, source="fast_path_low_confidence")

        if self._looks_like_learning_candidate(normalized):
            return self._result("learning", confidence=0.62, should_learn=True, source="local_learning_candidate")

        return None

    def _result(self, intent, target="", confidence=0.0, should_use_llm_response=False, should_learn=False, operation="", structured_request=None, source="intent_interpreter"):
        request = structured_request or {}
        if operation and not request.get("operation"):
            request = dict(request)
            request["operation"] = operation
        return {
            "intent": intent if intent in self.VALID_INTENTS else "unknown",
            "target": target,
            "confidence": self._confidence(confidence),
            "should_use_llm_response": bool(should_use_llm_response),
            "should_learn": bool(should_learn or intent == "learning"),
            "should_query_world_model": intent in {"world_query", "question_about_user"},
            "should_query_self_model": intent in {"identity", "creator_query", "self_status"},
            "should_use_reasoning": intent == "reasoning",
            "should_use_agency": intent == "agency",
            "summary": intent,
            "structured_request": request,
            "source": source,
        }

    def _normalize(self, parsed, source):
        if not isinstance(parsed, dict):
            return None
        intent = str(parsed.get("intent") or "unknown").strip().lower()
        if intent not in self.VALID_INTENTS:
            intent = "unknown"
        structured = parsed.get("structured_request") if isinstance(parsed.get("structured_request"), dict) else {}
        return {
            "intent": intent,
            "target": str(parsed.get("target") or "").strip(),
            "confidence": self._confidence(parsed.get("confidence"), 0.0),
            "should_use_llm_response": bool(parsed.get("should_use_llm_response", intent in {"small_talk", "conversation"})),
            "should_learn": bool(parsed.get("should_learn", intent == "learning")),
            "should_query_world_model": bool(parsed.get("should_query_world_model", intent in {"world_query", "question_about_user"})),
            "should_query_self_model": bool(parsed.get("should_query_self_model", intent in {"identity", "creator_query", "self_status"})),
            "should_use_reasoning": bool(parsed.get("should_use_reasoning", intent == "reasoning")),
            "should_use_agency": bool(parsed.get("should_use_agency", intent == "agency")),
            "summary": str(parsed.get("summary") or intent).strip(),
            "structured_request": structured,
            "source": source,
        }

    def _parse_json(self, raw_text):
        raw = str(raw_text or "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _normalize_text(self, text):
        normalized = str(text or "").strip().lower()
        replacements = {
            "á": "a", "à": "a", "ã": "a", "â": "a",
            "é": "e", "ê": "e",
            "í": "i",
            "ó": "o", "ô": "o", "õ": "o",
            "ú": "u",
            "ç": "c",
            "¿": "", "?": "", "!": "", ".": "", ",": "",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        while "  " in normalized:
            normalized = normalized.replace("  ", " ")
        return normalized

    def _confidence(self, value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))

    def _contains_any(self, normalized, markers):
        return any(self._normalize_text(marker) in normalized for marker in markers)

    def _starts_with_any(self, normalized, markers):
        return any(normalized.startswith(self._normalize_text(marker)) for marker in markers)

    def _approval_route(self, normalized):
        approvals = {"sim", "yes", "si", "claro", "pode", "autorizo", "confirmo", "ok", "beleza"}
        rejections = {"nao", "não", "no", "negativo", "cancela", "cancelar", "nao salve", "não salve"}
        if normalized in approvals:
            return self._result("system", confidence=0.96, operation="approval", structured_request={"operation": "approval"}, source="fast_path")
        if normalized in rejections:
            return self._result("system", confidence=0.96, operation="rejection", structured_request={"operation": "rejection"}, source="fast_path")
        return None

    def _is_error_query(self, normalized):
        return self._contains_any(normalized, ["ultimo erro", "último erro", "erro", "falha", "problema hoje", "stacktrace"])

    def _error_operation(self, normalized):
        if self._contains_any(normalized, ["grave", "gravidade", "critico", "crítico"]):
            return "severity"
        if self._contains_any(normalized, ["onde", "corrigir", "correcao", "correção"]):
            return "where"
        return "last_error"

    def _is_creator_query(self, normalized):
        return self._contains_any(normalized, ["quem te criou", "quem criou voce", "quem criou você", "criador", "created you", "creador"])

    def _is_identity_query(self, normalized):
        return self._contains_any(normalized, ["quem e voce", "quem é você", "who are you", "quien eres", "quién eres", "do que voce e feita", "do que você é feita"])

    def _is_status_query(self, normalized):
        return self._contains_any(normalized, ["como voce esta", "como você está", "voce esta funcionando", "você está funcionando", "funcionando corretamente", "status", "operacional"])

    def _is_capability_query(self, normalized):
        return self._contains_any(normalized, ["o que voce consegue fazer", "o que você consegue fazer", "voce consegue fazer", "você consegue fazer", "capacidades", "capabilities", "capaz de fazer"])

    def _is_technical_capability_query(self, normalized):
        return self._contains_any(normalized, ["tecnicamente", "modulos", "módulos", "arquitetura", "estrutura tecnica", "estrutura técnica"])

    def _is_system_query(self, normalized):
        return self._contains_any(normalized, ["git", "repositorio", "repositório", "branch", "commit", "voz", "voice", "provider", "falar", "fala", "desktop", "configuracao", "configuração"])

    def _system_operation(self, normalized):
        if self._contains_any(normalized, ["voz", "voice", "provider", "falar", "fala"]):
            return "voice", "voice_status"
        if self._contains_any(normalized, ["branch"]):
            return "git", "branch"
        if self._contains_any(normalized, ["commit", "historico", "histórico", "evolucao", "evolução"]):
            return "git", "history"
        if self._contains_any(normalized, ["git", "repositorio", "repositório"]):
            return "git", "summary"
        return "system", "status"

    def _generic_who_target(self, normalized):
        starters = ["quem e ", "quem é ", "who is ", "quien es ", "quién es "]
        for starter in starters:
            clean = self._normalize_text(starter)
            if normalized.startswith(clean):
                target = normalized[len(clean):].strip()
                if target:
                    return target
        return ""

    def _looks_like_greeting_only(self, normalized):
        greetings = {"oi", "ola", "olá", "hello", "hi", "hola", "hey", "bom dia", "boa tarde", "boa noite", "buenos dias"}
        normalized_greetings = {self._normalize_text(item) for item in greetings}
        if normalized in normalized_greetings:
            return True
        tokens = normalized.split()
        if len(tokens) <= 3:
            return any(normalized.startswith(item + " ") for item in normalized_greetings)
        return False

    def _looks_like_learning_candidate(self, normalized):
        tokens = [token for token in normalized.split() if token]
        if len(tokens) < 4:
            return False
        if self._looks_like_greeting_only(normalized) or self._looks_like_small_talk(normalized):
            return False
        return True

    def _looks_like_small_talk(self, normalized):
        return self._contains_any(normalized, ["tudo bem", "como vai", "how are you", "como foi seu dia", "como foi o dia", "que tal"])

    def _elapsed(self, started_at):
        return int((time.perf_counter() - started_at) * 1000)
