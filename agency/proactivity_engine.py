from agency.json_utils import parse_json_object, clamp


class ProactivityEngine:
    """Generates proactive suggestions from observations, without fixed topics."""

    def __init__(self, memory, llm_provider=None, context_builder=None, logger=None):
        self.memory = memory
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger

    def propose(self):
        observations = self._observations()
        if not observations:
            return None
        if not self.llm_provider:
            return None
        prompt = self._build_prompt(observations)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            parsed = self._normalize(parse_json_object(result.text))
            if parsed.get("should_initiate"):
                return parsed
            return None
        except Exception as error:
            if self.logger:
                self.logger.log("PROACTIVITY_ENGINE_ERROR", str(error))
            return None

    def _observations(self):
        rows = []
        for row in self.memory.list_mid_term_memory(include_expired=False)[:20]:
            _id, summary, topics, source_count, created_at, expires_at, importance_score, promoted = row
            rows.append({
                "kind": "mid_term_pattern",
                "summary": summary,
                "topics": topics,
                "source_count": source_count,
                "importance_score": importance_score,
            })
        for row in self.memory.list_reasoning_conclusions("hypothesis")[:10]:
            _id, category, statement, confidence, evidence_json, origin, created_at = row
            rows.append({
                "kind": "hypothesis",
                "statement": statement,
                "confidence": confidence,
                "origin": origin,
            })
        return rows

    def _build_prompt(self, observations):
        context = self.context_builder.build("") if self.context_builder else ""
        return f"""
Você é o Proactivity Engine da Athena.

Com base apenas nas observações estruturadas, decida se faz sentido iniciar uma conversa.
Não use tópicos fixos.
Não use regras por domínio.
Não execute ações.
Peça autorização humana se sugerir uma ação.
Retorne SOMENTE JSON válido.

Schema:
{{
  "should_initiate": true,
  "message": "string",
  "reason": "string",
  "confidence": 0.0,
  "suggested_next_step": "string"
}}

Contexto:
{context}

Observações:
{observations}
""".strip()

    def _normalize(self, parsed):
        if not isinstance(parsed, dict):
            return {"should_initiate": False}
        message = str(parsed.get("message") or "").strip()
        return {
            "should_initiate": bool(parsed.get("should_initiate", False)) and bool(message),
            "message": message,
            "reason": str(parsed.get("reason") or "").strip(),
            "confidence": clamp(parsed.get("confidence"), 0.5),
            "suggested_next_step": str(parsed.get("suggested_next_step") or "").strip(),
        }
