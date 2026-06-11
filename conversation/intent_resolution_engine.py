import json
import time


class IntentResolutionEngine:
    """
    LLM-guided intent and target resolution.

    This module is intentionally LLM-first. It does not contain linguistic
    keyword trees, phrase parsers, domain rules, or hardcoded entity handling.
    Its job is to ask the language module for a compact JSON structure and then
    normalize that structure defensively for Athena Core.
    """

    VALID_INTENTS = {
        "self_identity",
        "user_identity",
        "creator_query",
        "entity_query",
        "capability_query",
        "capabilities",
        "capability",
        "technical_capability",
        "self_status",
        "memory_query",
        "world_query",
        "reasoning",
        "learning",
        "agency",
        "system",
        "teach_intent",
        "error_query",
        "external_information",
        "small_talk",
        "greeting",
        "conversation",
        "unknown",
    }

    VALID_TARGET_TYPES = {"self", "user", "entity", "world", "tool", "unknown"}

    def __init__(self, llm_provider=None, identity=None, logger=None, settings=None, tool_registry=None):
        self.llm_provider = llm_provider
        self.identity = identity or {}
        self.logger = logger
        self.settings = settings
        self.tool_registry = tool_registry

    def resolve(self, user_input, session_context=None, pending_state=None):
        started_at = time.perf_counter()
        if self.settings and not self.settings.get("useLLM", True):
            return self._unavailable_result(started_at, "LLM desativada em config/settings.json")
        if not self.llm_provider:
            return self._unavailable_result(started_at, "LLM provider não inicializado")

        prompt = self._build_prompt(user_input, session_context, pending_state)
        try:
            result = self._generate_intent(prompt)
            if not result.available or not result.text:
                error = result.error if result else "sem resposta da LLM"
                return self._unavailable_result(started_at, error)
            parsed = self._parse_json(result.text)
            normalized = self._normalize(parsed)
            normalized["duration_ms"] = self._elapsed(started_at)
            return normalized
        except Exception as error:
            if self.logger:
                self.logger.log("INTENT_RESOLUTION_ERROR", str(error))
            return self._unavailable_result(started_at, str(error))

    def _generate_intent(self, prompt):
        timeout = None
        if self.settings:
            timeout = self.settings.get("intentResolutionTimeoutSeconds", self.settings.get("llmTimeoutSeconds", 30))
        try:
            return self.llm_provider.generate(prompt, timeout_seconds=timeout)
        except TypeError:
            return self.llm_provider.generate(prompt)

    def _build_prompt(self, user_input, session_context=None, pending_state=None):
        creator = self.identity.get("creator", "Rewell")
        athena_name = self.identity.get("name", "Athena")
        recent = session_context.summary(limit=4) if session_context else ""
        pending = pending_state or {}
        tools = self._tool_capability_summary()

        return f"""
Você é o módulo de resolução de intenção e alvo da Athena.
Retorne SOMENTE JSON válido, sem markdown, sem comentários e sem explicações.
Não responda ao usuário.
Não extraia fatos completos de mundo.
Apenas interprete a intenção, o alvo e quais subsistemas podem ser necessários.

Princípio arquitetural:
- A LLM interpreta linguagem.
- Athena Core decide, consulta memória, consulta World Model, aciona ferramentas e persiste.
- Se o usuário pedir informação externa e não houver ferramenta compatível, indique requires_tool=true e tool_name com a capacidade necessária.
- Se houver saudação + pergunta, classifique pela pergunta principal.
- Se houver saudação + pedido de informação externa atual, classifique pelo pedido externo, não pela saudação.
- Se o usuário afirmar algo novo sobre pessoas, relações, planos, preferências, identidade do usuário ou relação com Athena, classifique como learning.
- Se o usuário pedir visualização técnica, debug ou relações estruturadas, mantenha a intenção principal e coloque structured_request.mode="technical".
- Se o usuário pedir explicação de uma conclusão anterior, classifique como reasoning e coloque structured_request.operation="explain_last_conclusion".
- Não invente conhecimento factual.

Identidade mínima:
- Nome da entidade: {athena_name}
- Usuário/criador principal: {creator}

Intenções permitidas:
self_identity, user_identity, creator_query, entity_query, capability_query, capabilities, capability, technical_capability,
self_status, memory_query, world_query, reasoning, learning, agency, system, teach_intent,
error_query, external_information, small_talk, greeting, conversation, unknown

Tipos de alvo permitidos:
self, user, entity, world, tool, unknown

Ferramentas/capacidades registradas:
{tools}

Schema obrigatório:
{{
  "intent": "",
  "target": "",
  "target_type": "unknown",
  "confidence": 0.0,
  "requires_memory": false,
  "requires_world_model": false,
  "requires_reasoning": false,
  "requires_tool": false,
  "tool_name": null,
  "should_learn": false,
  "should_use_llm_response": true,
  "summary": "",
  "structured_request": {{}}
}}

Orientação de decisão:
- Pergunta sobre Athena: intent=self_identity, target_type=self.
- Pergunta sobre capacidades, habilidades ou o que Athena pode fazer: intent=capability_query, target_type=self.
- Pergunta sobre o usuário/criador: intent=user_identity, target_type=user, requires_memory=true.
- Pergunta sobre entidade/pessoa/objeto/conceito conhecido: intent=entity_query, target_type=entity, requires_world_model=true, requires_memory=true.
- Informação nova fornecida pelo usuário: intent=learning, should_learn=true.
- Pedido explícito para ensinar Athena: intent=teach_intent, target_type=self.
- Pedido de informação externa não disponível internamente: intent=external_information, target_type=tool, requires_tool=true.
- Afirmação nova sobre a relação usuário-Athena: intent=learning, target_type=self ou user conforme o alvo principal, should_learn=true.
- Pergunta operacional sobre Git/voz/configuração/status: intent=system ou self_status.
- Pergunta sobre erro/falha: intent=error_query.

Estado pendente:
{json.dumps(pending, ensure_ascii=False)}

Contexto recente curto:
{recent}

Mensagem do usuário:
{user_input}
""".strip()

    def _tool_capability_summary(self):
        if not self.tool_registry:
            return "Nenhuma ferramenta registrada no contexto atual."
        try:
            tools = self.tool_registry.list_available()
        except Exception as error:
            if self.logger:
                self.logger.log("INTENT_TOOL_SUMMARY_ERROR", str(error))
            return "Não foi possível listar ferramentas agora."
        if not tools:
            return "Nenhuma ferramenta registrada no contexto atual."
        lines = []
        for tool in tools[:20]:
            lines.append(f"- id={tool.get('id')} | capability={tool.get('capability')} | confidence={tool.get('confidence')}")
        return "\n".join(lines)

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

    def _normalize(self, parsed):
        if not isinstance(parsed, dict):
            return self._base_result(source="llm_invalid_json", confidence=0.0)

        intent = self._clean_label(parsed.get("intent"))
        if intent not in self.VALID_INTENTS:
            intent = "unknown"

        target_type = self._clean_label(parsed.get("target_type"))
        if target_type not in self.VALID_TARGET_TYPES:
            target_type = "unknown"

        structured = parsed.get("structured_request") if isinstance(parsed.get("structured_request"), dict) else {}
        confidence = self._confidence(parsed.get("confidence"), 0.0)
        requires_tool = bool(parsed.get("requires_tool", intent == "external_information"))
        tool_name = parsed.get("tool_name")
        if tool_name is not None:
            tool_name = str(tool_name).strip() or None

        result = self._base_result(source="llm_intent_resolution", confidence=confidence)
        result.update({
            "intent": intent,
            "target": str(parsed.get("target") or "").strip(),
            "target_type": target_type,
            "requires_memory": bool(parsed.get("requires_memory", intent in {"user_identity", "entity_query", "memory_query"})),
            "requires_world_model": bool(parsed.get("requires_world_model", intent in {"entity_query", "world_query"})),
            "requires_reasoning": bool(parsed.get("requires_reasoning", intent == "reasoning")),
            "requires_tool": requires_tool,
            "tool_name": tool_name,
            "should_learn": bool(parsed.get("should_learn", intent == "learning")),
            "should_use_llm_response": bool(parsed.get("should_use_llm_response", intent in {"small_talk", "conversation"})),
            "summary": str(parsed.get("summary") or intent).strip(),
            "structured_request": structured,
        })
        return result

    def _base_result(self, source="intent_resolution", confidence=0.0):
        return {
            "intent": "unknown",
            "target": "",
            "target_type": "unknown",
            "confidence": self._confidence(confidence),
            "requires_memory": False,
            "requires_world_model": False,
            "requires_reasoning": False,
            "requires_tool": False,
            "tool_name": None,
            "should_learn": False,
            "should_use_llm_response": False,
            "summary": "unknown",
            "structured_request": {},
            "source": source,
            "available": True,
            "error": "",
        }

    def _unavailable_result(self, started_at, error):
        result = self._base_result(source="llm_intent_unavailable", confidence=0.0)
        result.update({
            "available": False,
            "error": str(error or "LLM indisponível"),
            "summary": "intent_resolution_unavailable",
            "duration_ms": self._elapsed(started_at),
        })
        return result

    def _clean_label(self, value):
        clean = str(value or "").strip().lower()
        chars = []
        for char in clean:
            if char.isalnum() or char in {"_", "-"}:
                chars.append(char)
            else:
                chars.append("_")
        label = "".join(chars)
        while "__" in label:
            label = label.replace("__", "_")
        return label.strip("_")

    def _confidence(self, value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))

    def _elapsed(self, started_at):
        return int((time.perf_counter() - started_at) * 1000)
