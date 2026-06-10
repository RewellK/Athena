class EventEngine:
    def __init__(self, memory, entity_engine):
        self.memory = memory
        self.entity_engine = entity_engine

    def save(self, name, event_type="generic_event", date=None, description=""):
        event_id = self.memory.save_world_event(name, event_type, date, description)
        return event_id

    def add_participant(self, event_id, entity, role="participant"):
        self.entity_engine.ensure_entity(entity)
        self.memory.save_world_event_participant(event_id, entity, role)

    def answer_structural(self, event_name=None, event_type=None, participant=None, role=None):
        rows = self.memory.list_world_events(event_type=event_type)
        filtered = []
        for row in rows:
            event_id, name, kind, date, description, created_at = row
            participants = self.memory.list_world_event_participants(event_id)
            include = True
            if event_name and event_name.lower() not in name.lower():
                include = False
            if participant and not any(person.lower() == participant.lower() for person, _role in participants):
                include = False
            if role and not any(_role == role for _person, _role in participants):
                include = False
            if include:
                filtered.append((row, participants))
        if not filtered:
            return "Não encontrei eventos compatíveis no World Model."
        lines = ["Eventos estruturados:"]
        for row, participants in filtered[:30]:
            _id, name, kind, date, description, _created_at = row
            participant_text = ", ".join(f"{person} ({role})" for person, role in participants)
            lines.append(f"- {name} | tipo={kind} | data={date} | participantes={participant_text}")
        return "\n".join(lines)

    def list_all(self):
        return self.answer_structural()
