from world_model.entity_engine import EntityEngine
from world_model.relationship_engine import RelationshipEngine
from world_model.event_engine import EventEngine
from world_model.temporal_engine import TemporalEngine
from world_model.state_engine import StateEngine
from world_model.knowledge_extraction_engine import KnowledgeExtractionEngine
from world_model.confidence_engine import ConfidenceEngine
from world_model.query_understanding_engine import QueryUnderstandingEngine


class WorldModel:

    def __init__(self, memory, llm_provider=None, context_builder=None, logger=None, creator_name="Rewell", settings=None):
        self.memory = memory
        self.creator_name = creator_name
        self.entity_engine = EntityEngine(memory)
        self.relationship_engine = RelationshipEngine(memory, self.entity_engine)
        self.event_engine = EventEngine(memory, self.entity_engine)
        self.temporal_engine = TemporalEngine()
        self.state_engine = StateEngine(memory)
        self.confidence_engine = ConfidenceEngine()
        self.query_engine = QueryUnderstandingEngine(llm_provider, logger, creator_name)
        self.extraction_engine = KnowledgeExtractionEngine(
            llm_provider=llm_provider,
            context_builder=context_builder,
            temporal_engine=self.temporal_engine,
            logger=logger,
            creator_name=creator_name,
            settings=settings,
        )

    def propose(self, text, supplemental_context=None):
        extraction = self.extraction_engine.extract(text, supplemental_context=supplemental_context)
        decision = self.confidence_engine.evaluate_extraction(extraction)
        return extraction, decision

    def observe(self, text, force=False, supplemental_context=None):
        extraction, decision = self.propose(text, supplemental_context=supplemental_context)
        if not force and decision["decision"] != "save":
            self.memory.save_world_extraction(text, extraction, {"decision": decision["decision"], "saved": False})
            return {"entities": 0, "relationships": 0, "events": 0, "states": 0, "decision": decision, "extraction": extraction}
        saved = self.apply_extraction(extraction)
        saved["decision"] = decision
        saved["extraction"] = extraction
        self.memory.save_world_extraction(text, extraction, saved)
        return saved

    def apply_extraction(self, extraction):
        saved = {"entities": 0, "relationships": 0, "events": 0, "states": 0}

        for entity in extraction.get("entities", []):
            self.entity_engine.ensure_entity(entity.get("name"), entity.get("type", "unknown"))
            saved["entities"] += 1

        for relationship in extraction.get("relationships", []):
            self.relationship_engine.save(
                relationship.get("source"),
                relationship.get("relation"),
                relationship.get("target"),
                relationship.get("confidence", 0.70),
            )
            saved["relationships"] += 1

        for event in extraction.get("events", []):
            event_id = self.event_engine.save(
                event.get("name"),
                event.get("type", event.get("event_type", "generic_event")),
                event.get("date"),
                event.get("description", ""),
            )
            for participant in event.get("participants", []):
                entity_name = participant.get("entity") or participant.get("person")
                role = participant.get("role", "participant")
                if entity_name:
                    self.entity_engine.ensure_entity(entity_name)
                    self.memory.save_world_event_participant(event_id, entity_name, role)
            saved["events"] += 1

        for state in extraction.get("states", []):
            self.state_engine.set_state(
                state.get("entity"),
                state.get("attribute"),
                state.get("value"),
                state.get("source_event"),
                state.get("confidence", 0.70),
            )
            saved["states"] += 1

        return saved

    def answer(self, user_input):
        query = self.query_engine.understand(user_input)
        if query and query.get("confidence", 0) >= 0.60:
            return self._answer_structural_query(query)
        return None

    def _answer_structural_query(self, query):
        intent = query.get("intent")
        filters = query.get("filters", {})

        if intent == "list_entities":
            return self.entity_engine.list_by_type(filters.get("entity_type"))

        if intent == "list_relationships":
            return self.relationship_engine.list_all()

        if intent == "list_events":
            return self.event_engine.list_all()

        if intent == "list_states":
            return self.state_engine.list_all()

        if intent == "query_state":
            return self.state_engine.answer_structural(
                filters.get("state_entity") or filters.get("entity"),
                filters.get("state_attribute"),
            )

        if intent == "query_relationship":
            return self.relationship_engine.answer_structural(
                source=filters.get("source"),
                relation=filters.get("relation"),
                target=filters.get("target"),
            )

        if intent == "query_event":
            return self.event_engine.answer_structural(
                event_name=filters.get("event_name"),
                event_type=filters.get("event_type"),
                participant=filters.get("event_participant") or filters.get("entity"),
                role=filters.get("event_role"),
            )

        if intent == "query_entity":
            return self.entity_engine.answer_structural(
                entity=filters.get("entity"),
                entity_type=filters.get("entity_type"),
            )

        return None

    def summary(self):
        return (
            "World Model da Athena:\n"
            f"- Entidades: {self.memory.count_entities()}\n"
            f"- Relações estruturadas: {self.memory.count_world_relationships()}\n"
            f"- Eventos estruturados: {self.memory.count_world_events()}\n"
            f"- Estados atuais: {self.memory.count_entity_states()}"
        )

    def format_extraction_preview(self, extraction):
        parts = []
        if extraction.get("entities"):
            parts.append("Entidades: " + ", ".join(f"{e.get('name')} ({e.get('type')})" for e in extraction.get("entities", [])[:8]))
        if extraction.get("relationships"):
            parts.append("Relações: " + ", ".join(f"{r.get('source')} -> {r.get('relation')} -> {r.get('target')}" for r in extraction.get("relationships", [])[:8]))
        if extraction.get("events"):
            parts.append("Eventos: " + ", ".join(f"{e.get('name')} [{e.get('type')}]" for e in extraction.get("events", [])[:8]))
        if extraction.get("states"):
            parts.append("Estados: " + ", ".join(f"{s.get('entity')}.{s.get('attribute')} = {s.get('value')}" for s in extraction.get("states", [])[:8]))
        return "\n".join(parts) if parts else "Nenhuma estrutura clara encontrada."
