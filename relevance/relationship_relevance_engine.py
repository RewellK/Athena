class RelationshipRelevanceEngine:
    """Reads relationship density from already-structured knowledge.

    It does not interpret user text. The LLM extracts relationships; this class
    only counts and exposes structured signals so Athena Core can decide how
    much care to give the memory.
    """

    def structured_signals(self, extracted_knowledge=None):
        extraction = extracted_knowledge if isinstance(extracted_knowledge, dict) else {}
        entities = self.related_entities(extraction)
        relationships = extraction.get("relationships") if isinstance(extraction.get("relationships"), list) else []
        states = extraction.get("states") if isinstance(extraction.get("states"), list) else []
        events = extraction.get("events") if isinstance(extraction.get("events"), list) else []
        return {
            "related_entities": entities,
            "relationship_count": len(relationships),
            "state_count": len(states),
            "event_count": len(events),
            "has_structured_knowledge": bool(entities or relationships or states or events),
        }

    def related_entities(self, extracted_knowledge=None):
        extraction = extracted_knowledge if isinstance(extracted_knowledge, dict) else {}
        names = []
        for entity in self._items(extraction.get("entities")):
            name = str(entity.get("name") or "").strip()
            if name:
                names.append(name)
        for relation in self._items(extraction.get("relationships")):
            for key in ("source", "target"):
                name = str(relation.get(key) or "").strip()
                if name:
                    names.append(name)
        for state in self._items(extraction.get("states")):
            name = str(state.get("entity") or "").strip()
            if name:
                names.append(name)
        for event in self._items(extraction.get("events")):
            for participant in self._items(event.get("participants")):
                name = str(participant.get("entity") or participant.get("person") or "").strip()
                if name:
                    names.append(name)
        return self._unique(names)

    def _items(self, value):
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
        return []

    def _unique(self, values):
        seen = set()
        unique = []
        for value in values:
            marker = value.lower()
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(value)
        return unique
