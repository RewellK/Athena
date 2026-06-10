class RelationshipEngine:
    def __init__(self, memory, entity_engine):
        self.memory = memory
        self.entity_engine = entity_engine

    def save(self, source, relation, target, confidence=0.80):
        self.entity_engine.ensure_entity(source)
        self.entity_engine.ensure_entity(target)
        self.memory.save_world_relationship(source, relation, target, self._to_percent(confidence))

    def answer_structural(self, source=None, relation=None, target=None):
        rows = self.memory.list_world_relationships(source=source, relation=relation, target=target)
        if not rows:
            return "Não encontrei relações compatíveis no World Model."
        return "Relações estruturadas:\n" + "\n".join(
            f"- {src} -> {rel} -> {tgt} | confiança={confidence}"
            for _id, src, rel, tgt, confidence, _created_at in rows[:50]
        )

    def list_all(self):
        return self.answer_structural()

    def _to_percent(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.80
        if number <= 1:
            number *= 100
        return int(max(0, min(100, number)))
