class ContextBuilder:

    def __init__(self, memory, identity):
        self.memory = memory
        self.identity = identity

    def build(self, user_input):
        sections = [
            self._identity_context(),
            self._definitions_context(),
            self._relationships_context(),
            self._goals_context(),
            self._events_context(),
            self._memory_layers_context(),
            self._world_model_context(),
            self._instruction_context(),
            f"Mensagem do usuário: {user_input}"
        ]

        return "\n\n".join(section for section in sections if section.strip())

    def _identity_context(self):
        return (
            "IDENTIDADE DA ATHENA\n"
            f"Nome: {self.identity.get('name')}\n"
            f"Criador: {self.identity.get('creator')}\n"
            f"Propósito: {self.identity.get('purpose')}\n"
            "Princípio: Athena usa LLMs. LLMs não são Athena."
        )

    def _definitions_context(self):
        rows = self.memory.list_definitions()
        if not rows:
            return "DEFINIÇÕES CONHECIDAS\nNenhuma definição registrada."

        lines = [f"- {concept}: {meaning}" for concept, meaning in rows[:20]]
        return "DEFINIÇÕES CONHECIDAS\n" + "\n".join(lines)

    def _relationships_context(self):
        rows = self.memory.list_relationships()
        if not rows:
            return "RELACIONAMENTOS CONHECIDOS\nNenhum relacionamento registrado."

        lines = [f"- {source} -> {relation} -> {target}" for source, relation, target, _created_at in rows[:30]]
        return "RELACIONAMENTOS CONHECIDOS\n" + "\n".join(lines)

    def _goals_context(self):
        rows = self.memory.list_goals()
        if not rows:
            return "OBJETIVOS CONHECIDOS\nNenhum objetivo registrado."

        lines = [
            f"- {owner}: {goal} | status={status} | prioridade={priority}"
            for owner, goal, status, priority, _created_at in rows[:30]
        ]
        return "OBJETIVOS CONHECIDOS\n" + "\n".join(lines)

    def _events_context(self):
        rows = self.memory.list_events()
        if not rows:
            return "EVENTOS CONHECIDOS\nNenhum evento registrado."

        lines = []
        for event_id, name, event_date, description, _created_at in rows[:30]:
            participants = self.memory.list_event_participants(event_id)
            participant_text = ", ".join(f"{person} ({role})" for person, role in participants)
            line = f"- {name} | data={event_date} | descrição={description}"
            if participant_text:
                line += f" | participantes={participant_text}"
            lines.append(line)

        return "EVENTOS CONHECIDOS\n" + "\n".join(lines)

    def _memory_layers_context(self):
        short_rows = self.memory.list_short_term_memory()
        mid_rows = self.memory.list_mid_term_memory()
        lines = [
            "CAMADAS DE MEMÓRIA",
            f"Memórias curtas ativas: {self.memory.count_short_term_memory()}",
            f"Memórias médias ativas: {self.memory.count_mid_term_memory()}",
            f"Memórias longas estimadas: {self.memory.count_long_term_memory()}",
        ]

        if short_rows:
            lines.append("Memória curta recente:")
            lines.extend(f"- {row[1]} | score={row[5]}" for row in short_rows[-10:])

        if mid_rows:
            lines.append("Memória intermediária:")
            lines.extend(f"- {row[1]} | fontes={row[3]} | score={row[6]}" for row in mid_rows[:10])

        if hasattr(self.memory, "list_memory_relevance"):
            relevance_rows = self.memory.list_memory_relevance(limit=10)
            if relevance_rows:
                lines.append("Relevância humana recente:")
                for row in relevance_rows:
                    _id, layer, _layer_id, content, _source_message, relevance_score, _importance_score, emotional_score, relationship_score, identity_score, future_score, memory_priority, _entities, _confirmation_required, _confirmed, _follow_up, _reason, _created_at = row
                    lines.append(
                        f"- {content} | layer={layer} | priority={memory_priority} | "
                        f"relevance={relevance_score} | emotional={emotional_score} | relationship={relationship_score} | "
                        f"identity={identity_score} | future={future_score}"
                    )

        return "\n".join(lines)

    def _world_model_context(self):
        lines = [
            "WORLD MODEL",
            f"Entidades: {self.memory.count_entities()}",
            f"Relações estruturadas: {self.memory.count_world_relationships()}",
            f"Eventos estruturados: {self.memory.count_world_events()}",
            f"Estados atuais: {self.memory.count_entity_states()}",
        ]

        entities = self.memory.list_entities()[:20]
        if entities:
            lines.append("Entidades conhecidas:")
            lines.extend(f"- {name} ({entity_type})" for _id, name, entity_type, _created_at in entities)

        relationships = self.memory.list_world_relationships()[:20]
        if relationships:
            lines.append("Relações estruturadas:")
            lines.extend(
                f"- {source} -> {relation} -> {target} | confiança={confidence}"
                for _id, source, relation, target, confidence, _created_at in relationships
            )

        states = self.memory.list_entity_states()[:20]
        if states:
            lines.append("Estados atuais:")
            lines.extend(
                f"- {entity}.{attribute} = {value} | confiança={confidence}"
                for _id, entity, attribute, value, _event, confidence, _created_at, _updated_at in states
            )

        return "\n".join(lines)

    def _instruction_context(self):
        return (
            "INSTRUÇÕES DE RESPOSTA\n"
            "Responda como Athena, uma entidade digital persistente em evolução. "
            "Use o contexto persistente como fonte principal. "
            "Não invente memórias. Se algo não estiver no contexto, diga que ainda não sabe. "
            "Pode formar opiniões, mas elas devem ser baseadas nos dados conhecidos da Athena Core. "
            "Responda em português brasileiro, de forma natural e breve."
        )
