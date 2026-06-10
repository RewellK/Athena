class StateEngine:
    def __init__(self, memory):
        self.memory = memory

    def set_state(self, entity, attribute, value, source_event=None, confidence=0.80):
        self.memory.save_entity_state(entity, attribute, value, source_event, self._to_percent(confidence))

    def answer_structural(self, entity=None, attribute=None):
        if entity and attribute:
            state = self.memory.get_entity_state(entity, attribute)
            if state:
                entity_name, attr, value, source_event, confidence, created_at, updated_at = state
                return f"Estado atual: {entity_name}.{attr} = {value} | confiança={confidence} | atualizado={updated_at}"
        states = self.memory.list_entity_states(entity_name=entity)
        if not states:
            return "Não encontrei estados atuais compatíveis."
        return "Estados atuais conhecidos:\n" + "\n".join(
            f"- {entity_name}.{attr} = {value} | confiança={confidence}"
            for _id, entity_name, attr, value, _event, confidence, _created_at, _updated_at in states[:50]
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
