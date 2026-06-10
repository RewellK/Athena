from agency.json_utils import parse_json_object, clamp


class GoalEngine:
    """Transforms structured intentions into candidate agency goals."""

    def __init__(self, memory, llm_provider=None, context_builder=None, logger=None):
        self.memory = memory
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger

    def propose_goal(self, intention_id, intention):
        if not self.llm_provider:
            return None
        prompt = self._build_prompt(intention)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            parsed = self._normalize(parse_json_object(result.text))
            if not parsed.get("should_create_goal"):
                return None
            goal_id = self.memory.save_agency_goal(
                intention_id,
                parsed["description"],
                rationale=parsed["rationale"],
                priority=parsed["priority"],
                confidence=parsed["confidence"],
                status="proposed",
            )
            parsed["id"] = goal_id
            return parsed
        except Exception as error:
            if self.logger:
                self.logger.log("GOAL_ENGINE_ERROR", str(error))
            return None

    def _build_prompt(self, intention):
        context = self.context_builder.build("") if self.context_builder else ""
        return f"""
Você é o Goal Engine da Athena.

Transforme uma intenção estruturada em objetivo somente se isso fizer sentido.
Não use templates por domínio.
Não crie objetivo se a intenção for apenas conversa comum ou pergunta simples.
Retorne SOMENTE JSON válido.

Schema:
{{
  "should_create_goal": true,
  "description": "string",
  "rationale": "string",
  "priority": 0.0,
  "confidence": 0.0
}}

Contexto persistente:
{context}

Intenção:
{intention}
""".strip()

    def _normalize(self, parsed):
        if not isinstance(parsed, dict):
            return {"should_create_goal": False}
        description = str(parsed.get("description") or "").strip()
        return {
            "should_create_goal": bool(parsed.get("should_create_goal", False)) and bool(description),
            "description": description,
            "rationale": str(parsed.get("rationale") or "").strip(),
            "priority": clamp(parsed.get("priority"), 0.5),
            "confidence": clamp(parsed.get("confidence"), 0.5),
        }
