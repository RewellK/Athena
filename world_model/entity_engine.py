class EntityEngine:
    def __init__(self, memory):
        self.memory = memory

    def ensure_entity(self, name, entity_type="unknown"):
        if not name:
            return None
        self.memory.save_entity(name, entity_type or "unknown")
        rows = self.memory.find_entities(name_fragment=name)
        return rows[0] if rows else None

    def answer_structural(self, entity=None, entity_type=None):
        if entity:
            rows = self.memory.find_entities(name_fragment=entity)
            if not rows:
                return "Não encontrei essa entidade no meu World Model."
            return "Entidades encontradas:\n" + "\n".join(f"- {name} ({kind})" for _id, name, kind, _created_at in rows[:20])
        return self.list_by_type(entity_type)

    def list_by_type(self, entity_type=None):
        rows = self.memory.list_entities(entity_type=entity_type)
        if not rows:
            return "Ainda não tenho entidades desse tipo registradas."
        return "Entidades conhecidas:\n" + "\n".join(f"- {name} ({kind})" for _id, name, kind, _created_at in rows[:50])
