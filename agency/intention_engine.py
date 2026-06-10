from agency.json_utils import parse_json_object, clamp, ensure_list


class IntentionEngine:
    """
    V11 LLM-first intention layer.

    This module does not use keyword triggers, regex, or domain rules.
    It asks the language module to return structure only. Athena Core then
    validates confidence and decides what to coordinate.
    """

    VALID_TYPES = {
        "conversation",
        "knowledge_input",
        "question",
        "reflection_request",
        "self_model_request",
        "reasoning_request",
        "curiosity_request",
        "knowledge_source_request",
        "agency_request",
        "approval",
        "rejection",
        "correction",
        "unknown",
    }

    VALID_ROUTES = {
        "world_model",
        "reasoning",
        "reflection",
        "self_model",
        "curiosity",
        "knowledge_sources",
        "agency",
        "conversation",
        "none",
    }

    def __init__(self, llm_provider=None, context_builder=None, logger=None):
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger

    def interpret(self, user_input, pending_state=None):
        if not self.llm_provider:
            return self._unavailable()
        prompt = self._build_prompt(user_input, pending_state)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return self._unavailable()
            parsed = parse_json_object(result.text)
            return self._normalize(parsed)
        except Exception as error:
            if self.logger:
                self.logger.log("INTENTION_ENGINE_ERROR", str(error))
            return self._unavailable()

    def _build_prompt(self, user_input, pending_state=None):
        context = ""
        if self.context_builder:
            context = self.context_builder.build(user_input)
        pending_block = pending_state or {}
        return f"""
Você é o Intention Engine da Athena.

Sua função é transformar a mensagem do usuário em intenção estruturada.
Você NÃO responde ao usuário.
Você NÃO executa ações.
Você NÃO grava memória.
Você NÃO usa regras por palavras.
Você NÃO deve retornar markdown.
Retorne SOMENTE JSON válido.

A Athena deve depender de intenção, não de palavras.
A mesma estrutura deve funcionar em português, inglês e espanhol.
Se a intenção for ambígua, reduza confidence e defina needs_clarification=true.

Tipos permitidos:
conversation, knowledge_input, question, reflection_request, self_model_request,
reasoning_request, curiosity_request, knowledge_source_request, agency_request,
approval, rejection, correction, unknown

Rotas permitidas:
world_model, reasoning, reflection, self_model, curiosity, knowledge_sources,
agency, conversation, none

Schema obrigatório:
{{
  "intention_type": "string",
  "route": "string",
  "goal": "string",
  "summary": "string",
  "requires_action": false,
  "requires_approval": true,
  "needs_clarification": false,
  "confidence": 0.0,
  "rationale": "string",
  "approval_target": "string_or_empty",
  "structured_request": {{}},
  "candidate_tools": ["capability_or_empty"]
}}

Contexto persistente resumido:
{context}

Estado pendente da conversa:
{pending_block}

Mensagem do usuário:
{user_input}
""".strip()

    def _normalize(self, parsed):
        if not isinstance(parsed, dict):
            return self._unknown(0.0, "A LLM não retornou JSON estrutural válido.")
        intention_type = str(parsed.get("intention_type") or "unknown").strip().lower()
        route = str(parsed.get("route") or "none").strip().lower()
        if intention_type not in self.VALID_TYPES:
            intention_type = "unknown"
        if route not in self.VALID_ROUTES:
            route = "none"
        return {
            "intention_type": intention_type,
            "route": route,
            "goal": str(parsed.get("goal") or "").strip(),
            "summary": str(parsed.get("summary") or "").strip(),
            "requires_action": bool(parsed.get("requires_action", False)),
            "requires_approval": bool(parsed.get("requires_approval", True)),
            "needs_clarification": bool(parsed.get("needs_clarification", False)),
            "confidence": clamp(parsed.get("confidence"), 0.0),
            "rationale": str(parsed.get("rationale") or "").strip(),
            "approval_target": str(parsed.get("approval_target") or "").strip(),
            "structured_request": parsed.get("structured_request") if isinstance(parsed.get("structured_request"), dict) else {},
            "candidate_tools": [str(item).strip() for item in ensure_list(parsed.get("candidate_tools")) if str(item).strip()],
            "source": "llm_structural_intention",
        }

    def _unknown(self, confidence, rationale):
        return {
            "intention_type": "unknown",
            "route": "none",
            "goal": "",
            "summary": "",
            "requires_action": False,
            "requires_approval": True,
            "needs_clarification": True,
            "confidence": clamp(confidence, 0.0),
            "rationale": rationale,
            "approval_target": "",
            "structured_request": {},
            "candidate_tools": [],
            "source": "intention_unknown",
        }

    def _unavailable(self):
        return self._unknown(0.0, "LLM indisponível para interpretação de intenção.")
