import json


class ConversationRouter:
    """Conversation-first route classifier.

    Primary path: LLM returns structured route JSON.
    Safety path: if LLM is unavailable, only obvious non-learning/system routes
    are handled locally. The safety path never creates knowledge and never calls
    Knowledge Extraction; it exists to keep Desktop usable when Ollama is off.
    """

    VALID_ROUTES = {
        "greeting",
        "small_talk",
        "identity",
        "capability",
        "self_status",
        "memory_query",
        "world_query",
        "reasoning",
        "learning",
        "agency",
        "system",
        "error_query",
        "conversation",
        "unknown",
    }

    def __init__(self, llm_provider=None, context_builder=None, logger=None):
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger

    def route(self, user_input, session_context=None, pending_state=None):
        llm_route = self._llm_route(user_input, session_context, pending_state)
        if llm_route:
            return llm_route
        return self._safe_local_route(user_input, pending_state)

    def _llm_route(self, user_input, session_context=None, pending_state=None):
        if not self.llm_provider:
            return None
        prompt = self._build_prompt(user_input, session_context, pending_state)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            parsed = self._parse_json(result.text)
            normalized = self._normalize(parsed, source="llm_conversation_router")
            if normalized.get("confidence", 0) <= 0:
                return None
            return normalized
        except Exception as error:
            if self.logger:
                self.logger.log("CONVERSATION_ROUTER_ERROR", str(error))
            return None

    def _build_prompt(self, user_input, session_context=None, pending_state=None):
        persistent_context = ""
        if self.context_builder:
            persistent_context = self.context_builder.build(user_input)
        recent_context = session_context.summary() if session_context else ""
        pending = pending_state or {}
        routes = ", ".join(sorted(self.VALID_ROUTES - {"unknown"}))
        return f"""
Você é o Conversation Router da Athena.

Sua função é classificar a mensagem em uma rota conversacional.
Você NÃO responde ao usuário.
Você NÃO grava memória.
Você NÃO extrai conhecimento.
Você NÃO cria entidades, eventos, estados ou relações.
Você deve retornar SOMENTE JSON válido.

Princípio central: conversar vem antes de aprender.
A rota learning só deve ser usada quando a mensagem realmente trouxer informação nova que o usuário parece querer ensinar ou registrar.
Perguntas simples, saudações, conversa casual, identidade, capacidade, status e erros NÃO devem ir para learning.

Rotas permitidas:
{routes}

Schema obrigatório:
{{
  "route": "string",
  "intent": "string",
  "summary": "string",
  "confidence": 0.0,
  "needs_clarification": false,
  "should_learn": false,
  "structured_request": {{}}
}}

Use structured_request.operation quando a rota precisar de uma operação genérica.
Operações úteis, sem depender de palavras exatas:
- identity: describe_self
- capability: describe_capabilities
- self_status: health
- error_query: last_error, severity, where, impact
- system: git_status, git_branch, voice_status, settings, desktop
- memory_query: summary, today, week, counts
- world_query: entities, relationships, events, states, answer
- reasoning: explain, beliefs, hypotheses, why

Estado pendente:
{json.dumps(pending, ensure_ascii=False)}

Contexto da sessão:
{recent_context}

Contexto persistente resumido:
{persistent_context}

Mensagem:
{user_input}
""".strip()

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

    def _normalize(self, parsed, source):
        if not isinstance(parsed, dict):
            return self._unknown(source)
        route = str(parsed.get("route") or "unknown").strip().lower()
        if route not in self.VALID_ROUTES:
            route = "unknown"
        confidence = self._confidence(parsed.get("confidence"), 0.0)
        return {
            "route": route,
            "intent": str(parsed.get("intent") or "").strip(),
            "summary": str(parsed.get("summary") or "").strip(),
            "confidence": confidence,
            "needs_clarification": bool(parsed.get("needs_clarification", False)),
            "should_learn": bool(parsed.get("should_learn", route == "learning")),
            "structured_request": parsed.get("structured_request") if isinstance(parsed.get("structured_request"), dict) else {},
            "source": source,
        }

    def _safe_local_route(self, user_input, pending_state=None):
        text = str(user_input or "").strip()
        normalized = self._normalize_text(text)
        pending_type = (pending_state or {}).get("pending_type")

        if pending_type and pending_type != "none":
            approval = self._approval_route(normalized)
            if approval:
                return approval

        if not normalized:
            return self._route("conversation", "empty_message", 0.40, source="local_safety_fallback")

        # This fallback intentionally covers only non-learning UX/system routes.
        # It is not used to persist knowledge and it must remain conservative.
        greeting_markers = {"oi", "ola", "hello", "hi", "buenos dias", "bom dia", "boa tarde", "boa noite", "hola", "hey"}
        if normalized in greeting_markers or any(normalized.startswith(marker + " ") for marker in greeting_markers):
            return self._route("greeting", "greeting", 0.95, source="local_safety_fallback")

        if self._contains_any(normalized, {"como voce esta", "como voce está", "how are you functioning", "funcionando corretamente", "operacional"}):
            return self._route("self_status", "self_status", 0.85, {"operation": "health"}, source="local_safety_fallback")

        if self._contains_any(normalized, {"tudo bem", "como vai", "how are you", "que tal", "como fue tu dia", "como foi seu dia"}):
            return self._route("small_talk", "small_talk", 0.85, source="local_safety_fallback")

        if self._contains_any(normalized, {"quem e voce", "quem é você", "do que voce e feita", "do que você é feita", "who are you"}):
            return self._route("identity", "identity", 0.90, {"operation": "describe_self"}, source="local_safety_fallback")

        if self._contains_any(normalized, {"o que voce consegue fazer", "o que você consegue fazer", "capacidades", "capabilities", "capaz de fazer"}):
            return self._route("capability", "capability", 0.90, {"operation": "describe_capabilities"}, source="local_safety_fallback")

        if self._contains_any(normalized, {"status"}):
            return self._route("self_status", "self_status", 0.85, {"operation": "health"}, source="local_safety_fallback")

        if self._contains_any(normalized, {"ultimo erro", "último erro", "teve algum problema", "erro grave", "onde devo corrigir", "o que aconteceu com o erro"}):
            operation = "last_error"
            if self._contains_any(normalized, {"grave", "gravidade", "critico", "crítico"}):
                operation = "severity"
            elif self._contains_any(normalized, {"onde", "corrigir", "correcao", "correção"}):
                operation = "where"
            return self._route("error_query", "error_query", 0.90, {"operation": operation, "focus": operation}, source="local_safety_fallback")

        if self._contains_any(normalized, {"git", "repositorio", "repositório", "branch", "commit"}):
            operation = "summary"
            if self._contains_any(normalized, {"branch"}):
                operation = "branch"
            elif self._contains_any(normalized, {"commit", "historico", "histórico", "evolucao", "evolução"}):
                operation = "history"
            return self._route("system", "git_status", 0.80, {"subsystem": "git", "operation": operation}, source="local_safety_fallback")

        if self._contains_any(normalized, {"falar", "voz", "voice", "provider"}):
            return self._route("system", "voice_status", 0.75, {"subsystem": "voice", "operation": "status"}, source="local_safety_fallback")

        return self._route("conversation", "conversation", 0.60, source="local_safety_fallback")

    def _approval_route(self, normalized):
        approvals = {"sim", "yes", "si", "claro", "pode", "autorizo", "confirmo", "ok", "beleza"}
        rejections = {"nao", "não", "no", "negativo", "cancela", "cancelar", "nao salve", "não salve"}
        if normalized in approvals:
            return self._route("system", "approval", 0.95, {"operation": "approval"}, source="local_safety_fallback")
        if normalized in rejections:
            return self._route("system", "rejection", 0.95, {"operation": "rejection"}, source="local_safety_fallback")
        return None

    def _route(self, route, intent, confidence, structured_request=None, source="conversation_router"):
        return {
            "route": route,
            "intent": intent,
            "summary": intent,
            "confidence": self._confidence(confidence, 0.0),
            "needs_clarification": False,
            "should_learn": route == "learning",
            "structured_request": structured_request or {},
            "source": source,
        }

    def _unknown(self, source):
        return self._route("unknown", "unknown", 0.0, source=source)

    def _confidence(self, value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))

    def _normalize_text(self, text):
        normalized = str(text or "").strip().lower()
        replacements = {
            "á": "a", "à": "a", "ã": "a", "â": "a",
            "é": "e", "ê": "e",
            "í": "i",
            "ó": "o", "ô": "o", "õ": "o",
            "ú": "u",
            "ç": "c",
            "?": "", "!": "", ".": "", ",": "",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        while "  " in normalized:
            normalized = normalized.replace("  ", " ")
        return normalized

    def _contains_any(self, normalized, markers):
        return any(self._normalize_text(marker) in normalized for marker in markers)
