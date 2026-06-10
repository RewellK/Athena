import json


class QueryUnderstandingEngine:
    """
    Converts user questions into generic World Model query structures.
    No domain-specific names, verbs, relations, or object classes are encoded here.
    """

    def __init__(self, llm_provider=None, logger=None, creator_name="Rewell"):
        self.llm_provider = llm_provider
        self.logger = logger
        self.creator_name = creator_name

    def understand(self, question):
        if not self.llm_provider:
            return None
        prompt = self._build_prompt(question)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            parsed = self._parse_json(result.text)
            return self._normalize(parsed)
        except Exception as error:
            if self.logger:
                self.logger.log("WORLD_QUERY_ERROR", f"Falha ao interpretar consulta do World Model: {error}")
            return None

    def _build_prompt(self, question):
        return f"""
Você é o interpretador estrutural de consultas do World Model da Athena.

Converta a pergunta do usuário em JSON genérico.
Não responda à pergunta.
Não explique.
Não use markdown.
Retorne SOMENTE JSON válido.

Princípios:
- Não dependa de nomes específicos.
- Não dependa de verbos específicos.
- Não dependa de relações específicas.
- Inferir semanticamente filtros, atributos, entidades, relações, eventos e papéis.
- Pronomes de primeira pessoa relacionados ao criador devem ser normalizados como "{self.creator_name}".
- Se a consulta for ambígua, use confidence menor.

Schema:
{{
  "intent": "list_entities|list_relationships|list_events|list_states|query_entity|query_relationship|query_event|query_state|unknown",
  "filters": {{
    "entity": "string_or_empty",
    "entity_type": "string_or_empty",
    "source": "string_or_empty",
    "relation": "string_or_empty",
    "target": "string_or_empty",
    "event_name": "string_or_empty",
    "event_type": "string_or_empty",
    "event_participant": "string_or_empty",
    "event_role": "string_or_empty",
    "state_entity": "string_or_empty",
    "state_attribute": "string_or_empty"
  }},
  "confidence": 0.0
}}

Pergunta:
{question}
""".strip()

    def _parse_json(self, raw_text):
        raw = raw_text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            parsed = json.loads(raw[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
        return None

    def _normalize(self, parsed):
        if not isinstance(parsed, dict):
            return None
        intent = self._clean_label(parsed.get("intent"))
        filters = parsed.get("filters") if isinstance(parsed.get("filters"), dict) else {}
        confidence = self._normalize_confidence(parsed.get("confidence"), 0.60)
        return {
            "intent": intent or "unknown",
            "filters": {key: self._clean_text(value) for key, value in filters.items()},
            "confidence": confidence,
        }

    def _clean_text(self, value):
        return "" if value is None else str(value).strip()

    def _clean_label(self, value):
        clean = self._clean_text(value).lower()
        chars = []
        for char in clean:
            if char.isalnum() or char in ["_", "-"]:
                chars.append(char)
            else:
                chars.append("_")
        label = "".join(chars)
        while "__" in label:
            label = label.replace("__", "_")
        return label.strip("_")

    def _normalize_confidence(self, value, default=0.60):
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = default
        if confidence > 1:
            confidence = confidence / 100
        return max(0.0, min(1.0, confidence))
