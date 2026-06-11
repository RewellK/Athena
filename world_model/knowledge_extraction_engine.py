import json

class KnowledgeExtractionEngine:
    """
    V8.2 — LLM-first structural extraction.

    This class must not contain domain intelligence based on fixed names,
    verbs, family terms, commerce verbs, travel verbs, or growing linguistic
    regex lists.

    The LLM interprets language and returns structure.
    Athena Core validates, decides, and persists.
    """

    VALID_ENTITY_TYPES = {
        "person",
        "object",
        "place",
        "concept",
        "project",
        "organization",
        "event",
        "unknown",
    }

    REQUIRED_KEYS = [
        "entities",
        "relationships",
        "events",
        "states",
        "temporal_references",
    ]

    def __init__(
        self,
        llm_provider=None,
        context_builder=None,
        temporal_engine=None,
        logger=None,
        creator_name="Rewell",
        settings=None,
    ):
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.temporal_engine = temporal_engine
        self.logger = logger
        self.creator_name = creator_name
        self.settings = settings

    def extract(self, text, supplemental_context=None):
        llm_extraction = self._llm_extract(text, supplemental_context)

        if llm_extraction:
            return self._normalize_extraction(llm_extraction, source="llm")

        if self.logger:
            self.logger.log("KNOWLEDGE_EXTRACTION", "LLM unavailable and regex fallback disabled. Athena will ask for clarification instead of guessing.")

        return self._empty_extraction(source="llm_unavailable")

    def _llm_extract(self, text, supplemental_context=None):
        if not self.llm_provider:
            return None
        if self.settings and not self.settings.get("useLLM", True):
            return None

        prompt = self._build_extraction_prompt(text, supplemental_context)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            return self._parse_json(result.text)
        except Exception as error:
            if self.logger:
                self.logger.log("KNOWLEDGE_EXTRACTION_ERROR", f"Falha na extração estrutural com LLM: {error}")
            return None

    def _build_extraction_prompt(self, text, supplemental_context=None):
        context_block = ""
        if supplemental_context:
            context_block = f"\nContexto adicional fornecido pelo Athena Core:\n{supplemental_context}\n"

        return f"""
Você é o módulo estrutural de extração de conhecimento da Athena.

Sua tarefa é converter texto livre em JSON estrutural genérico.
Você NÃO é a Athena inteira.
Você NÃO grava memória.
Você NÃO responde ao usuário.
Você NÃO explica.
Você NÃO deve retornar markdown.
Você deve retornar SOMENTE JSON válido.

Princípios obrigatórios:
- Não dependa de nomes específicos.
- Não dependa de exemplos específicos.
- Não trate nenhum domínio como especial.
- Interprete a estrutura sem inventar fatos.
- Se houver ambiguidade, reduza confidence.
- Se uma informação não puder ser extraída com segurança, deixe a lista correspondente vazia.
- Pronomes de primeira pessoa relacionados ao criador devem ser normalizados como "{self.creator_name}".
- Use o contexto adicional para resolver pronomes e referências indiretas quando houver evidência suficiente.
- Se uma mensagem expressar múltiplas relações, planos, estados ou eventos, retorne múltiplos itens estruturados em vez de compactar tudo em uma única relação.
- Relações emocionais, relacionais, identitárias e futuras podem coexistir; represente cada significado estruturalmente se estiver sustentado pelo texto.
- Tipos, relações, eventos, papéis e atributos devem ser rótulos genéricos em snake_case inferidos semanticamente do texto.

Schema obrigatório:
{{
  "entities": [
    {{
      "name": "string",
      "type": "person|object|place|concept|project|organization|event|unknown",
      "confidence": 0.0
    }}
  ],
  "relationships": [
    {{
      "source": "string",
      "relation": "string_snake_case",
      "target": "string",
      "confidence": 0.0
    }}
  ],
  "events": [
    {{
      "name": "string",
      "type": "string_snake_case",
      "date": "string_or_empty",
      "description": "string",
      "participants": [
        {{"entity": "string", "role": "string_snake_case"}}
      ],
      "confidence": 0.0
    }}
  ],
  "states": [
    {{
      "entity": "string",
      "attribute": "string_snake_case",
      "value": "string",
      "source_event": "string_or_empty",
      "confidence": 0.0
    }}
  ],
  "temporal_references": [
    {{
      "text": "string",
      "normalized": "string_or_empty",
      "confidence": 0.0
    }}
  ]
}}
{context_block}
Texto do usuário:
{text}
""".strip()

    def _parse_json(self, raw_text):
        raw = raw_text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            parsed = json.loads(raw[start:end + 1])
            if not isinstance(parsed, dict):
                return None
            return parsed
        except json.JSONDecodeError:
            return None

    def _empty_extraction(self, source="empty"):
        return {
            "entities": [],
            "relationships": [],
            "events": [],
            "states": [],
            "temporal_references": [],
            "source": source,
        }

    def _normalize_extraction(self, extraction, source):
        normalized = self._empty_extraction(source=source)
        if not isinstance(extraction, dict):
            return normalized

        for entity in self._as_list(extraction.get("entities")) :
            if not isinstance(entity, dict):
                continue
            name = self._clean_text(entity.get("name"))
            if not name:
                continue
            entity_type = self._clean_label(entity.get("type", "unknown"))
            if entity_type not in self.VALID_ENTITY_TYPES:
                entity_type = "unknown"
            normalized["entities"].append({
                "name": name,
                "type": entity_type,
                "confidence": self._normalize_confidence(entity.get("confidence")),
            })

        for relationship in self._as_list(extraction.get("relationships")) :
            if not isinstance(relationship, dict):
                continue
            source_name = self._clean_text(relationship.get("source"))
            relation = self._clean_label(relationship.get("relation"))
            target = self._clean_text(relationship.get("target"))
            if not source_name or not relation or not target:
                continue
            normalized["relationships"].append({
                "source": source_name,
                "relation": relation,
                "target": target,
                "confidence": self._normalize_confidence(relationship.get("confidence")),
            })

        for event in self._as_list(extraction.get("events")) :
            if not isinstance(event, dict):
                continue
            event_type = self._clean_label(event.get("type") or event.get("event_type") or "generic_event")
            name = self._clean_text(event.get("name")) or self._build_generic_event_name(event_type, event)
            participants = []
            for participant in self._as_list(event.get("participants")) :
                if not isinstance(participant, dict):
                    continue
                entity = self._clean_text(participant.get("entity") or participant.get("person"))
                role = self._clean_label(participant.get("role") or "participant")
                if entity:
                    participants.append({"entity": entity, "role": role})
            normalized["events"].append({
                "name": name,
                "type": event_type,
                "date": self._clean_text(event.get("date")),
                "description": self._clean_text(event.get("description")),
                "participants": participants,
                "confidence": self._normalize_confidence(event.get("confidence")),
            })

        for state in self._as_list(extraction.get("states")) :
            if not isinstance(state, dict):
                continue
            entity = self._clean_text(state.get("entity"))
            attribute = self._clean_label(state.get("attribute"))
            value = self._clean_text(state.get("value"))
            if not entity or not attribute or not value:
                continue
            normalized["states"].append({
                "entity": entity,
                "attribute": attribute,
                "value": value,
                "source_event": self._clean_text(state.get("source_event")),
                "confidence": self._normalize_confidence(state.get("confidence")),
            })

        for temporal in self._as_list(extraction.get("temporal_references")) :
            if not isinstance(temporal, dict):
                continue
            text = self._clean_text(temporal.get("text"))
            normalized_value = self._clean_text(temporal.get("normalized"))
            if not text and not normalized_value:
                continue
            normalized["temporal_references"].append({
                "text": text,
                "normalized": normalized_value,
                "confidence": self._normalize_confidence(temporal.get("confidence")),
            })

        self._deduplicate(normalized)
        return normalized

    def _as_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
        return []

    def _build_generic_event_name(self, event_type, event):
        event_type = self._clean_label(event_type or "generic_event")
        participants = []
        for participant in self._as_list(event.get("participants")) if isinstance(event, dict) else []:
            if isinstance(participant, dict):
                entity = self._clean_text(participant.get("entity") or participant.get("person"))
                if entity:
                    participants.append(entity)
        date = self._clean_text(event.get("date")) if isinstance(event, dict) else ""
        base_parts = [event_type]
        if participants:
            base_parts.append("_".join(self._clean_label(item) for item in participants[:3]))
        if date:
            base_parts.append(self._clean_label(date))
        name = "_".join(part for part in base_parts if part).strip("_")
        return name or "generic_event"

    def _clean_text(self, value):
        if value is None:
            return ""
        return str(value).strip()

    def _clean_label(self, value):
        clean = self._clean_text(value).lower()
        allowed = []
        for char in clean:
            if char.isalnum() or char in ["_", "-"]:
                allowed.append(char)
            else:
                allowed.append("_")
        label = "".join(allowed)
        while "__" in label:
            label = label.replace("__", "_")
        label = label.strip("_")
        return label or "unknown"

    def _normalize_confidence(self, value, default=0.70):
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = default
        if confidence > 1:
            confidence = confidence / 100
        return max(0.0, min(1.0, confidence))

    def _deduplicate(self, extraction):
        extraction["entities"] = self._unique_dicts(extraction["entities"], ["name", "type"])
        extraction["relationships"] = self._unique_dicts(extraction["relationships"], ["source", "relation", "target"])
        extraction["events"] = self._unique_dicts(extraction["events"], ["name", "type", "date"])
        extraction["states"] = self._unique_dicts(extraction["states"], ["entity", "attribute", "value"])
        extraction["temporal_references"] = self._unique_dicts(extraction["temporal_references"], ["text", "normalized"])

    def _unique_dicts(self, rows, keys):
        seen = set()
        unique = []
        for row in rows:
            marker = tuple(str(row.get(key, "")).lower() for key in keys)
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(row)
        return unique
