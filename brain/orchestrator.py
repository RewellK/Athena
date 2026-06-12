import json
import time
from datetime import datetime

from agency.action_engine import ActionEngine
from audio.message_sound import MessageSoundEngine
from agency.agency_engine import AgencyEngine
from agency.goal_engine import GoalEngine
from agency.intention_engine import IntentionEngine
from agency.proactivity_engine import ProactivityEngine
from agency.tool_registry import ToolRegistry
from bootstrap import AthenaBootstrap
from core.context_builder import ContextBuilder
from core.logger import AthenaLogger
from core.settings import Settings
from conversation.capability_engine import CapabilityEngine
from conversation.conversation_context import ConversationContext
from conversation.conversation_engine import ConversationEngine
from conversation.conversation_router import ConversationRouter
from conversation.conversation_metrics import ConversationMetrics
from conversation.identity_engine import IdentityEngine
from conversation.self_status_engine import SelfStatusEngine
from curiosity.curiosity_engine import CuriosityEngine
from error_awareness.error_capture import ErrorCapture
from error_awareness.error_reporter import ErrorReporter
from forgetting_engine import ForgettingEngine
from git_awareness.git_awareness_engine import GitAwarenessEngine
from health.health_engine import HealthEngine
from knowledge_sources.knowledge_ingestion_engine import KnowledgeIngestionEngine
from learning.learning_engine import LearningEngine
from llm.provider import OllamaProvider
from memory.database import MemoryDB
from memory_interpreter import MemoryInterpreter
from memory_manager.memory_manager import MemoryManager
from relevance.consolidation_planner import ConsolidationPlanner
from relevance.follow_up_question_engine import FollowUpQuestionEngine
from relevance.relevance_engine import RelevanceEngine
from reasoning.reasoning_engine import ReasoningEngine
from reflection.reflection_engine import ReflectionEngine
from self_model.self_model import SelfModel
from self_code_awareness.self_code_awareness_engine import SelfCodeAwarenessEngine
from sources.source_manager import SourceManager
from voice.voice_engine import VoiceEngine
from world_model.world_model import WorldModel


class Athena:
    """
    V12.2 conversation-first orchestrator.

    The Orchestrator coordinates and delegates. It does not perform knowledge
    extraction as the entry point. Every user message first passes through the
    Conversation Router; only the learning route reaches Knowledge Extraction.
    """

    def __init__(self):
        self.logger = AthenaLogger()
        self.error_capture = ErrorCapture(self.logger)
        self.error_reporter = ErrorReporter()
        self.memory = MemoryDB()
        AthenaBootstrap(self.memory).run()

        with open("personality/identity.json", "r", encoding="utf-8") as file:
            self.identity = json.load(file)

        self.creator_name = self.identity["creator"]
        self.settings = Settings()
        self.context_builder = ContextBuilder(self.memory, self.identity)
        self.llm_provider = OllamaProvider(self.settings, self.logger)
        self.git_awareness_engine = GitAwarenessEngine(
            self.settings.get("projectRoot", "."),
            self.settings.get("officialRepositoryUrl", "https://github.com/RewellK/Athena/"),
        )
        self.self_code_awareness_engine = SelfCodeAwarenessEngine(
            self.settings.get("projectRoot", "."),
            settings=self.settings,
            git_reader=self.git_awareness_engine.repository_reader,
        )

        self.tool_registry = ToolRegistry(self.memory)
        self.tool_registry.bootstrap()

        self.intention_engine = IntentionEngine(self.llm_provider, self.context_builder, self.logger)
        self.memory_interpreter = MemoryInterpreter(self.llm_provider, self.context_builder, self.logger)
        self.memory_manager = MemoryManager(self.memory, self.memory_interpreter, self.creator_name)
        self.relevance_engine = RelevanceEngine(self.llm_provider, self.identity, self.logger, self.settings)
        self.follow_up_question_engine = FollowUpQuestionEngine(self.llm_provider, self.identity, self.logger, self.settings)
        self.consolidation_planner = ConsolidationPlanner()
        self.learning_engine = LearningEngine(self.memory, self.creator_name)
        self.world_model = WorldModel(
            self.memory,
            self.llm_provider,
            self.context_builder,
            self.logger,
            self.creator_name,
            self.settings,
        )
        self.reasoning_engine = ReasoningEngine(
            self.memory,
            self.identity,
            self.llm_provider,
            self.context_builder,
            logger=self.logger,
        )
        self.reflection_engine = ReflectionEngine(
            self.memory,
            self.identity,
            self.context_builder,
            self.llm_provider,
            settings=self.settings,
            logger=self.logger,
        )
        self.self_model = SelfModel(self.memory, self.identity, self.settings, self.llm_provider, self.context_builder)
        self.curiosity_engine = CuriosityEngine(self.memory, self.memory_manager, self.creator_name, self.llm_provider, self.context_builder)
        self.proactivity_engine = ProactivityEngine(self.memory, self.llm_provider, self.context_builder, self.logger)
        self.knowledge_ingestion_engine = KnowledgeIngestionEngine(
            self.memory,
            self.world_model,
            self.llm_provider,
            self.context_builder,
            self.logger,
            self.settings,
        )
        self.goal_engine = GoalEngine(self.memory, self.llm_provider, self.context_builder, self.logger)
        self.action_engine = ActionEngine(self.memory, self.tool_registry, self.llm_provider, self.context_builder, self.logger)
        self.agency_engine = AgencyEngine(self.memory, self.goal_engine, self.action_engine, self.logger)
        self.forgetting_engine = ForgettingEngine(self.memory)
        self.voice_engine = VoiceEngine(self.settings, self.logger)
        self.message_sound_engine = MessageSoundEngine(self.settings, self.logger)
        self.conversation_metrics = ConversationMetrics(logger=self.logger)
        self.last_response_metadata = {}

        self.health_engine = HealthEngine(
            memory=self.memory,
            llm_provider=self.llm_provider,
            voice_engine=self.voice_engine,
            git_awareness_engine=self.git_awareness_engine,
            error_capture=self.error_capture,
        )
        self.conversation_context = ConversationContext()
        self.conversation_router = ConversationRouter(
            self.llm_provider,
            self.context_builder,
            self.logger,
            identity=self.identity,
            settings=self.settings,
            tool_registry=self.tool_registry,
            relevance_engine=self.relevance_engine,
        )
        self.conversation_engine = ConversationEngine(
            identity=self.identity,
            llm_provider=self.llm_provider,
            context_builder=self.context_builder,
            health_engine=self.health_engine,
            logger=self.logger,
            settings=self.settings,
        )
        self.identity_engine = IdentityEngine(self.identity, self.self_model)
        self.capability_engine = CapabilityEngine(
            self_code_awareness_engine=self.self_code_awareness_engine,
            git_awareness_engine=self.git_awareness_engine,
            voice_engine=self.voice_engine,
            settings=self.settings,
        )
        self.self_status_engine = SelfStatusEngine(self.health_engine, self.error_capture)
        self.source_manager = SourceManager(settings=self.settings, logger=self.logger)

        self.pending_world_extraction = None
        self.pending_knowledge_ingestion = None
        self.pending_plan = None
        self.pending_source_proposal = None
        self.pending_history = []
        self.last_unknown_interaction = None

    def chat(self, user_input):
        try:
            return self._chat_impl(user_input)
        except Exception as error:
            return self.handle_exception(error, {"module": "brain/orchestrator.py", "operation": "chat"})

    def _chat_impl(self, user_input):
        started_at = self.conversation_metrics.start()
        self.message_sound_engine.play_received()
        self.conversation_context.add_user_message(user_input)
        self._expire_pending_confirmations()
        had_pending_before = self._has_pending_confirmation()
        llm_calls_before = self._llm_call_count()

        pending_control = self._pending_control(user_input)
        if pending_control:
            route_result = self._pending_route_result(pending_control)
        else:
            pending_state = self._pending_state()
            route_result = self.conversation_router.route(
                user_input,
                session_context=self.conversation_context,
                pending_state=pending_state,
            )

        intention = self._route_to_intention(route_result, user_input)
        intention_id = self.memory.save_intention(
            user_input,
            intention,
            confidence=intention.get("confidence", 0.0),
            status="observed",
        )
        self._remember_contextual_entities(intention=intention)

        relevance = route_result.get("relevance") if isinstance(route_result.get("relevance"), dict) else {}
        metadata = {
            "route": intention.get("route"),
            "intent": intention.get("intent"),
            "target": intention.get("target", ""),
            "confidence": intention.get("confidence", 0.0),
            "used_llm": route_result.get("source", "").startswith("llm"),
            "used_world_model": False,
            "used_memory": bool(route_result.get("requires_memory", False)),
            "used_reasoning": False,
            "used_agency": False,
            "used_voice": False,
            "used_sound": self.settings.get("messageReceivedSoundEnabled", True),
            "llm_calls": 0,
            "llm_call_count": 0,
            "_llm_calls_before": llm_calls_before,
            "local_fast_path": str(route_result.get("source", "")).startswith("local_"),
            "route_source": route_result.get("source", ""),
            "intent_interpretation_ms": route_result.get("intent_interpretation_ms", 0),
            "intent_llm_calls": route_result.get("intent_llm_calls", 0),
            "relevance_llm_calls": route_result.get("relevance_llm_calls", 0),
            "extraction_llm_calls": 0,
            "reasoning_llm_calls": 0,
            "natural_response_llm_calls": 0,
            "follow_up_llm_calls": 0,
            "relevance_ms": relevance.get("duration_ms", 0),
            "extraction_ms": 0,
            "world_query_ms": 0,
            "response_ms": 0,
            "tts_ms": 0,
            "tts_duration_ms": 0,
            "relevance_score": relevance.get("relevance_score", 0),
            "emotional_score": relevance.get("emotional_score", 0),
            "relationship_score": relevance.get("relationship_score", 0),
            "identity_score": relevance.get("identity_score", 0),
            "future_score": relevance.get("future_score", 0),
            "memory_priority": relevance.get("memory_priority", "ignore"),
            "saved_to_memory": False,
            "updated_world_model": False,
            "follow_up_generated": False,
            "pending_confirmation": self._pending_state().get("pending_type"),
            "required_tool": route_result.get("tool_name") if route_result.get("requires_tool") else None,
            "tool_available": False,
        }

        pending_response = self._handle_pending(intention, user_input)
        if pending_response:
            return self._finalize_response(pending_response, route_result, started_at, user_input, metadata)

        response = self._delegate_conversation_route(intention_id, intention, user_input, metadata)
        if response:
            response = self._with_pending_reminder(response, had_pending_before, pending_control, metadata)
            return self._finalize_response(response, route_result, started_at, user_input, metadata)

        fallback_calls_before = self._llm_call_count()
        fallback = self.conversation_engine.respond(user_input, route_result, self.conversation_context)
        self._add_llm_delta(metadata, "natural_response_llm_calls", fallback_calls_before)
        fallback = self._with_pending_reminder(fallback, had_pending_before, pending_control, metadata)
        return self._finalize_response(fallback, route_result, started_at, user_input, metadata)

    def startup_greeting(self, now=None, speak=None):
        started_at = time.perf_counter()
        current = now or datetime.now()
        hour = current.hour
        if 5 <= hour < 12:
            greeting = "Bom dia"
        elif 12 <= hour < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"
        response = f"{greeting}, {self.creator_name}. Athena iniciada. Estou pronta para conversar."
        should_speak = self.settings.get("startupGreetingSpeak", False)
        if speak is not None:
            should_speak = bool(speak)
        if should_speak:
            try:
                self.voice_engine.speak_startup(response)
            except Exception as error:
                self.handle_exception(error, {"module": "voice/voice_engine.py", "operation": "speak_startup"})
        self.last_response_metadata = {
            "route": "startup_greeting",
            "intent": "startup_greeting",
            "target": "",
            "used_llm": False,
            "llm_calls": 0,
            "intent_llm_calls": 0,
            "relevance_llm_calls": 0,
            "extraction_llm_calls": 0,
            "reasoning_llm_calls": 0,
            "natural_response_llm_calls": 0,
            "follow_up_llm_calls": 0,
            "used_world_model": False,
            "used_reasoning": False,
            "used_agency": False,
            "used_voice": bool(should_speak),
            "used_sound": False,
            "used_memory": False,
            "local_fast_path": True,
            "route_source": "local_startup_greeting",
            "llm_call_count": 0,
            "startup_ms": int((time.perf_counter() - started_at) * 1000),
            "tts_duration_ms": 0,
        }
        return response

    def _route_to_intention(self, route_result, user_input):
        route_result = route_result if isinstance(route_result, dict) else {}
        route = route_result.get("route", "unknown")
        intent = route_result.get("intent") or route
        structured_request = route_result.get("structured_request") if isinstance(route_result.get("structured_request"), dict) else {}
        operation = structured_request.get("operation") or intent or route

        intention_type_by_route = {
            "greeting": "conversation",
            "small_talk": "conversation",
            "conversation": "conversation",
            "identity": "self_model_request",
            "creator_query": "self_model_request",
            "question_about_user": "question",
            "capability": "self_code_request",
            "technical_capability": "self_code_request",
            "self_status": "self_model_request",
            "memory_query": "reflection_request",
            "world_query": "question",
            "reasoning": "reasoning_request",
            "learning": "knowledge_input",
            "agency": "agency_request",
            "system": "question",
            "teach_intent": "conversation",
            "pending_confirmation": "confirmation",
            "external_information": "tool_information_request",
            "error_query": "error_awareness_request",
            "unknown": "unknown",
        }

        legacy_route_by_route = {
            "memory_query": "reflection",
            "world_query": "world_model",
            "question_about_user": "world_model",
            "reasoning": "reasoning",
            "learning": "world_model",
            "agency": "agency",
            "external_information": "external_information",
            "error_query": "error_awareness",
        }

        if operation == "approval":
            intention_type = "approval"
        elif operation == "rejection":
            intention_type = "rejection"
        else:
            intention_type = intention_type_by_route.get(route, "unknown")

        return {
            "intention_type": intention_type,
            "route": route,
            "intent": intent,
            "target": route_result.get("target", ""),
            "target_type": route_result.get("target_type", "unknown"),
            "requires_tool": route_result.get("requires_tool", False),
            "tool_name": route_result.get("tool_name"),
            "requires_memory": route_result.get("requires_memory", False),
            "should_learn": bool(route_result.get("should_learn", route == "learning")),
            "legacy_route": legacy_route_by_route.get(route, "conversation"),
            "goal": route_result.get("summary", ""),
            "summary": route_result.get("summary", ""),
            "requires_action": route == "agency",
            "requires_approval": True,
            "needs_clarification": bool(route_result.get("needs_clarification", False)),
            "confidence": route_result.get("confidence", 0.0),
            "rationale": f"Conversation Router classified the message as {route}.",
            "approval_target": "",
            "structured_request": structured_request,
            "candidate_tools": [],
            "operation": operation,
            "relevance": route_result.get("relevance", {}),
            "original_route": route_result.get("original_route", route),
            "source": route_result.get("source", "conversation_router"),
            "raw_user_input": user_input,
            "should_use_llm_response": route_result.get("should_use_llm_response", False),
            "should_query_world_model": route_result.get("should_query_world_model", False),
            "should_query_self_model": route_result.get("should_query_self_model", False),
            "should_use_reasoning": route_result.get("should_use_reasoning", False),
            "should_use_agency": route_result.get("should_use_agency", False),
        }

    def _delegate_conversation_route(self, intention_id, intention, user_input, metadata=None):
        metadata = metadata if isinstance(metadata, dict) else {}
        route = intention.get("route")

        if route in {"greeting", "small_talk", "conversation"}:
            return self.conversation_engine.respond(user_input, intention, self.conversation_context)

        if route == "identity":
            operation = intention.get("operation") or self._structured_request(intention).get("operation")
            if operation == "relationship_to_user":
                return self._describe_self_relationship_to_user()
            return self.identity_engine.respond(user_input, operation=operation, target=intention.get("target"), intent=intention.get("intent"))

        if route == "question_about_user":
            return self._handle_question_about_user(intention, user_input, metadata)

        if route == "capability":
            return self._handle_capability_route(intention)

        if route == "technical_capability":
            return self.capability_engine.respond(technical=True)

        if route == "teach_intent":
            return self._handle_teach_intent_route()

        if route == "self_status":
            return self.self_status_engine.respond()

        if route == "error_query":
            return self._handle_error_awareness_route(intention)

        if route == "memory_query":
            return self.reflection_engine.respond(user_input)

        if route == "world_query":
            metadata["used_world_model"] = True
            query_started_at = time.perf_counter()
            response = self._handle_world_query(intention, user_input)
            metadata["world_query_ms"] = int((time.perf_counter() - query_started_at) * 1000)
            return response or self._natural_response(user_input, intention, metadata)

        if route == "reasoning":
            metadata["used_reasoning"] = True
            reasoning_calls_before = self._llm_call_count()
            response = self.reasoning_engine.respond(user_input, intention)
            self._add_llm_delta(metadata, "reasoning_llm_calls", reasoning_calls_before)
            return response

        if route == "learning":
            metadata["used_world_model"] = True
            return self._handle_learning_route(intention, user_input, metadata)

        if route == "agency":
            metadata["used_agency"] = True
            return self._handle_agency_route(intention_id, intention)

        if route == "external_information":
            return self._handle_external_information_route(intention, user_input, metadata)

        if route == "system":
            return self._handle_system_route(intention)

        if intention.get("needs_clarification") or intention.get("confidence", 0.0) < 0.45:
            local_conversation = self._try_local_conversation_fallback(user_input)
            if local_conversation:
                return local_conversation
            self._remember_unknown_classification(user_input, intention)
            return "Não entendi com segurança o que você quer agora. Pode me explicar de outro jeito?"

        return self._delegate(intention_id, intention, user_input)

    def _try_local_conversation_fallback(self, user_input):
        """Tiny UX fallback for greetings when intent resolution is unavailable."""
        words = set(self._normalize_local_phrase(user_input).split())
        if not words or len(words) > 10:
            return None
        greetings = {"oi", "ola", "opa", "eai", "bom", "boa"}
        small_talk = {"bem", "tranquilo", "tranquila", "tudo"}
        if words & greetings and words & small_talk:
            return self.conversation_engine.respond(user_input, {"route": "small_talk"}, self.conversation_context)
        if words & greetings:
            return self.conversation_engine.respond(user_input, {"route": "greeting"}, self.conversation_context)
        return None

    def _normalize_local_phrase(self, text):
        normalized = str(text or "").strip().lower()
        replacements = {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        chars = []
        for char in normalized:
            chars.append(char if char.isalnum() else " ")
        return " ".join("".join(chars).split())

    def _handle_question_about_user(self, intention, user_input, metadata=None):
        target = str(intention.get("target") or "").strip()
        creator = self.creator_name
        if target and target.lower() == creator.lower():
            return self.identity_engine.describe_creator()

        metadata = metadata if isinstance(metadata, dict) else {}
        metadata["used_world_model"] = True
        response = self.world_model.answer(user_input)
        if response:
            return response

        if target:
            entity_answer = self._describe_entity_from_memory(
                target,
                technical=self._wants_technical_output(intention),
                user_input=user_input,
            )
            if entity_answer:
                return entity_answer
            return f"Ainda não tenho informações suficientes sobre {target}."

        return "Ainda não tenho informações suficientes sobre essa pessoa ou entidade."


    def _handle_world_query(self, intention, user_input):
        target = str(intention.get("target") or "").strip()
        request = self._structured_request(intention)
        if request.get("operation") == "user_relation_query":
            relation_answer = self._answer_user_relation_query(target)
            if relation_answer:
                return relation_answer
            return f"Ainda não tenho informações suficientes sobre {target}."
        if target:
            entity_answer = self._describe_entity_from_memory(
                target,
                technical=self._wants_technical_output(intention),
                user_input=user_input,
            )
            if entity_answer:
                return entity_answer
            return f"Ainda não tenho informações suficientes sobre {target}."
        response = self.world_model.answer(user_input)
        if response:
            return response
        return None

    def _describe_entity_from_memory(self, target, technical=False, user_input=""):
        rows = self.memory.find_entities(name_fragment=target, limit=10)
        exact = None
        for row in rows:
            if str(row[1]).strip().lower() == target.strip().lower():
                exact = row
                break
        if exact is None and len(rows) == 1:
            exact = rows[0]
        if exact is None:
            return None

        _entity_id, name, entity_type, _created_at = exact
        relationships = self.memory.find_world_relationships(source=name) + self.memory.find_world_relationships(target=name)
        states = self.memory.list_entity_states(entity_name=name)
        events = self.memory.find_world_events(entity_name=name)

        if not technical:
            return self._format_entity_natural(user_input, name, entity_type, relationships, states, events)

        return self._format_entity_technical(name, entity_type, relationships, states, events)

    def _format_entity_technical(self, name, entity_type, relationships, states, events):
        lines = [f"{name} está registrado no meu World Model como {entity_type}."]
        if relationships:
            lines.append("O que sei estruturalmente:")
            for _id, source, relation, related_target, confidence, _created_at in relationships[:8]:
                lines.append(f"- {source} -> {relation} -> {related_target} | confiança={confidence}")
        if states:
            lines.append("Estados conhecidos:")
            for _id, entity, attribute, value, source_event, confidence, _created_at, updated_at in states[:8]:
                lines.append(f"- {entity}.{attribute} = {value} | confiança={confidence}")
        if events:
            lines.append("Eventos relacionados:")
            for _id, event_name, event_type, date, description, created_at in events[:6]:
                when = f" em {date}" if date else ""
                lines.append(f"- {event_name} [{event_type}]{when}")
        return "\n".join(lines)

    def _format_entity_natural(self, user_input, name, entity_type, relationships, states, events):
        facts = {
            "entity": {"name": name, "type": entity_type},
            "relationships": [
                {"source": source, "relation": relation, "target": target, "confidence": confidence}
                for _id, source, relation, target, confidence, _created_at in relationships[:12]
            ],
            "states": [
                {"entity": entity, "attribute": attribute, "value": value, "confidence": confidence}
                for _id, entity, attribute, value, _source_event, confidence, _created_at, _updated_at in states[:12]
            ],
            "events": [
                {"name": event_name, "type": event_type, "date": date, "description": description}
                for _id, event_name, event_type, date, description, _created_at in events[:8]
            ],
        }
        if self.settings.get("fastMemoryResponses", True):
            fast_response = self._format_entity_fast_natural(name, entity_type, relationships, states, events)
            if fast_response:
                return fast_response

        if self.llm_provider and self.settings.get("useNaturalResponses", True) and self.settings.get("useLLM", True):
            try:
                prompt = f"""
Você é o NaturalResponseEngine da Athena.
Responda naturalmente a consulta sobre uma entidade usando somente os fatos estruturados.
Não mostre tabela técnica, setas ou confiança por padrão.
Não invente fatos.
Se os fatos forem poucos, diga isso com honestidade.
Responda em português brasileiro, de forma breve.

Pergunta:
{user_input}

Fatos estruturados:
{json.dumps(facts, ensure_ascii=False, indent=2)}
""".strip()
                result = self.llm_provider.generate(prompt)
                if result.available and result.text:
                    return result.text.strip()
            except Exception as error:
                self.handle_exception(error, {"module": "brain/orchestrator.py", "operation": "format_entity_natural"})

        lines = [f"Pelo que sei, {name} está registrado como {entity_type}."]
        if relationships:
            relation_text = ", ".join(f"{source} {relation.replace('_', ' ')} {target}" for _id, source, relation, target, _confidence, _created_at in relationships[:4])
            lines.append(f"Também sei que: {relation_text}.")
        if states:
            state_text = ", ".join(f"{entity} tem {attribute.replace('_', ' ')} {value}" for _id, entity, attribute, value, _source_event, _confidence, _created_at, _updated_at in states[:4])
            lines.append(f"Estados registrados: {state_text}.")
        return " ".join(lines)

    def _format_entity_fast_natural(self, name, entity_type, relationships, states, events):
        sentences = []
        creator = str(self.creator_name or "").strip()
        seen = set()
        for _id, source, relation, target, _confidence, _created_at in relationships[:12]:
            sentence = self._relationship_sentence(name, source, relation, target, creator)
            marker = sentence.lower()
            if sentence and marker not in seen:
                seen.add(marker)
                sentences.append(sentence)
        if not sentences:
            if states:
                state_parts = [
                    f"{entity} tem {attribute.replace('_', ' ')} {value}"
                    for _id, entity, attribute, value, _source_event, _confidence, _created_at, _updated_at in states[:3]
                ]
                return f"Pelo que sei, {name} está registrado como {entity_type}. Também sei que: {', '.join(state_parts)}."
            return f"Pelo que sei, {name} está registrado como {entity_type}, mas ainda tenho poucos detalhes."
        return " ".join(sentences[:4])

    def _relationship_sentence(self, name, source, relation, target, creator):
        relation = str(relation or "").strip()
        source = str(source or "").strip()
        target = str(target or "").strip()
        if relation == "father_of" and source == name and target == creator:
            return f"{name} é seu pai."
        if relation == "girlfriend_of" and source == name and target == creator:
            return f"{name} é sua namorada."
        if relation == "future_spouse_of" and source == name and target == creator:
            return f"Você me contou que pretende se casar com {name}."
        if relation == "plans_to_marry" and source == creator and target == name:
            return f"Você me contou que pretende se casar com {name}."
        if relation == "love_of_life_of" and source == name and target == creator:
            return f"Você disse que {name} é o amor da sua vida."
        if relation == "emotionally_important_to" and source == name and target == creator:
            return f"{name} é alguém emocionalmente importante para você."
        if relation == "interested_in" and source == name:
            return f"{name} gosta de {target}."
        if relation == "owns" and source == name:
            return f"{name} tem um {target}."
        if source == name:
            return f"{name} {relation.replace('_', ' ')} {target}."
        if target == name:
            return f"{source} {relation.replace('_', ' ')} {name}."
        return ""


    def _handle_external_information_route(self, intention, user_input="", metadata=None):
        metadata = metadata if isinstance(metadata, dict) else {}
        requested_tool = str(intention.get("tool_name") or intention.get("target") or "fonte externa").strip() or "fonte externa"
        metadata["required_tool"] = requested_tool
        query = str(user_input or intention.get("raw_user_input") or requested_tool)
        request = self._structured_request(intention)
        source_manager = getattr(self, "source_manager", None)
        if source_manager:
            try:
                result = source_manager.handle_external_request(query, requested_tool=requested_tool)
                metadata["external_domain"] = result.get("domain")
                metadata["source_status"] = result.get("status")
                metadata["source_manager_ms"] = result.get("duration_ms", 0)
                metadata["source_available"] = bool(result.get("source"))
                metadata["tool_available"] = result.get("status") in {"job_created", "completed"}
                metadata["used_source"] = result.get("status") == "completed"
                metadata["source_id"] = (result.get("source") or {}).get("source_id")
                evidence = (result.get("job") or {}).get("evidence") or {}
                metadata["evidence_id"] = evidence.get("evidence_id")
                metadata["evidence_valid_until"] = evidence.get("valid_until")
                if result.get("proposal"):
                    proposal = result["proposal"]
                    metadata["source_proposal"] = proposal.get("name")
                    metadata["source_candidate_status"] = proposal.get("status")
                    self.pending_source_proposal = self._make_pending(
                        "source_candidate_approval",
                        f"Adicionar {proposal.get('name')} como fonte candidata para {source_manager.domain_label(result.get('domain'))}",
                        proposal=proposal,
                    )
                if result.get("job"):
                    metadata["external_research_job_id"] = result["job"].get("job_id")
                    metadata["external_research_job_status"] = result["job"].get("status")
                    metadata["async_jobs_pending"] = source_manager.worker.pending_count()
                    metadata["reflection_queue_size"] = metadata.get("reflection_queue_size", 0)
                return result.get("response")
            except Exception as error:
                self.handle_exception(error, {"module": "sources/source_manager.py", "operation": "handle_external_request"})

        domain = request.get("domain") or "unknown_external"
        metadata["external_domain"] = domain
        metadata["tool_available"] = False
        return (
            f"Ainda não possuo uma ferramenta/fonte configurada para consultar '{requested_tool}' em tempo real.\n"
            "Para evitar inventar informação externa, prefiro não responder como se eu tivesse acessado essa fonte."
        )

    def _find_matching_tool(self, requested_tool, available_tools):
        requested = str(requested_tool or "").strip().lower()
        if not requested:
            return None
        for tool in available_tools or []:
            text = f"{tool.get('id', '')} {tool.get('capability', '')}".lower()
            if requested in text:
                return tool
        return None

    def _handle_system_route(self, intention):
        request = self._structured_request(intention)
        subsystem = request.get("subsystem")
        operation = request.get("operation") or intention.get("operation")

        if operation == "unknown_recovery":
            return self._explain_last_unknown()

        if operation == "teach_intent":
            return self._handle_teach_intent_route()

        if subsystem == "voice" or operation == "voice_status":
            try:
                status = self.voice_engine.status()
                return (
                    f"Voz: {status.get('status')}.\n"
                    f"Provider atual: {status.get('provider')}.\n"
                    f"Último erro: {status.get('last_error') or 'nenhum'}."
                )
            except Exception as error:
                return self.handle_exception(error, {"module": "voice/voice_engine.py", "operation": "status"})

        if subsystem == "git" or operation in {"git_status", "git_branch", "branch", "history", "diff", "tracked_files", "read_only_policy"}:
            git_request = {"operation": operation if operation in {"summary", "status", "branch", "history", "diff", "tracked_files", "read_only_policy"} else "summary"}
            return self.git_awareness_engine.respond(git_request)

        return self.self_status_engine.respond()

    def _handle_capability_route(self, intention):
        request = self._structured_request(intention)
        operation = str(request.get("operation") or intention.get("intent") or "").strip().lower()
        technical = intention.get("intent") == "technical_capability" or operation in {"technical_modules", "technical_capability"}
        if request.get("limitations_query") and not technical:
            return self.capability_engine.limitations()
        response = self.capability_engine.respond(technical=technical)
        if request.get("positive_day_context") and not technical:
            return f"Que bom que seu dia foi bom, {self.creator_name}. Sobre o que eu posso fazer:\n\n{response}"
        return response

    def _handle_teach_intent_route(self):
        return f"Claro, {self.creator_name}. Pode me ensinar. Eu vou tentar estruturar o que você disser no meu World Model e pedir confirmação quando faltar segurança."

    def _remember_unknown_classification(self, user_input, intention):
        self.last_unknown_interaction = {
            "input": str(user_input or ""),
            "route": intention.get("route", "unknown") if isinstance(intention, dict) else "unknown",
            "intent": intention.get("intent", "unknown") if isinstance(intention, dict) else "unknown",
            "source": intention.get("source", "unknown") if isinstance(intention, dict) else "unknown",
            "summary": intention.get("summary", "") if isinstance(intention, dict) else "",
            "confidence": intention.get("confidence", 0.0) if isinstance(intention, dict) else 0.0,
        }

    def _explain_last_unknown(self):
        last_unknown = getattr(self, "last_unknown_interaction", None)
        if not last_unknown:
            return "Não tenho uma falha de classificação recente registrada. Se eu travar em uma intenção, eu consigo explicar o que ficou ambíguo."
        previous_input = last_unknown.get("input", "")
        if self._looks_like_capability_question(previous_input):
            return (
                "Eu falhei ao classificar sua intenção anterior. Você estava perguntando sobre minhas capacidades, "
                "então eu deveria ter respondido com o que consigo fazer."
            )
        source = last_unknown.get("source") or "roteador"
        try:
            confidence = float(last_unknown.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        return (
            "Eu falhei ao classificar sua intenção anterior com segurança. "
            f"A mensagem foi: \"{previous_input}\". "
            f"Minha rota ficou como {last_unknown.get('route', 'unknown')} via {source}, com confiança {confidence:.2f}. "
            "Eu deveria ter pedido uma reformulação mais específica em vez de repetir o mesmo fallback."
        )

    def _looks_like_capability_question(self, text):
        words = set(self._normalize_local_phrase(text).split())
        capability_terms = {"capacidade", "capacidades", "habilidade", "habilidades", "recursos"}
        action_terms = {"fazer", "faz", "consegue", "pode", "ajudar", "serve"}
        subject_terms = {"voce", "vc", "vce", str(self.identity.get("name") or "athena").strip().lower()}
        query_terms = {"o", "que", "oq", "oque", "qual", "quais", "como"}
        return bool(words & capability_terms) or bool(words & subject_terms and words & action_terms and words & query_terms)

    def _try_local_error_awareness(self, user_input):
        """Minimal operational fallback for error diagnostics when the LLM is offline.

        This is not a cognitive parser and does not create knowledge, intentions or
        domain behavior. It only protects the desktop UX for the latest internal
        error report.
        """
        last_error = self.error_capture.last_error()
        if not last_error:
            return None
        normalized = (user_input or "").strip().lower()
        diagnostic_markers = {"erro", "error", "falha", "corrigir", "correção", "grave", "gravidade", "aconteceu"}
        if not any(marker in normalized for marker in diagnostic_markers):
            return None
        if any(marker in normalized for marker in {"corrigir", "correção", "onde"}):
            return self.error_reporter.explain_last_error(last_error, focus="where")
        if any(marker in normalized for marker in {"grave", "gravidade", "crítico", "critico"}):
            return self.error_reporter.explain_last_error(last_error, focus="severity")
        return self.error_reporter.explain_last_error(last_error)

    def _delegate(self, intention_id, intention, user_input):
        route = intention.get("route")

        if route == "external_information":
            return self._handle_external_information_route(intention)

        if route == "knowledge_sources":
            return self._handle_knowledge_source_route(intention, user_input)

        if route == "error_awareness":
            return self._handle_error_awareness_route(intention)

        if route == "self_code_awareness":
            return self._handle_self_code_route(intention)

        if route == "git_awareness":
            return self._handle_git_route(intention)

        if route == "world_model":
            return self._handle_world_route(intention, user_input)

        if route == "reasoning":
            return self.reasoning_engine.respond(user_input, intention)

        if route == "reflection":
            return self.reflection_engine.respond(user_input)

        if route == "self_model":
            return self.self_model.respond(user_input)

        if route == "curiosity":
            return self.curiosity_engine.respond(user_input)

        if route == "agency" or intention.get("requires_action"):
            return self._handle_agency_route(intention_id, intention)

        if intention.get("intention_type") == "knowledge_input":
            return self._handle_learning_route(intention, user_input, {})

        if intention.get("intention_type") == "error_awareness_request":
            return self._handle_error_awareness_route(intention)

        if intention.get("intention_type") == "self_code_request":
            return self._handle_self_code_route(intention)

        if intention.get("intention_type") == "git_awareness_request":
            return self._handle_git_route(intention)

        if intention.get("intention_type") == "reflection_request":
            return self.reflection_engine.respond(user_input)

        if intention.get("intention_type") == "self_model_request":
            return self.self_model.respond(user_input)

        if intention.get("intention_type") == "reasoning_request":
            return self.reasoning_engine.respond(user_input, intention)

        return None


    def _handle_error_awareness_route(self, intention):
        request = self._structured_request(intention)
        focus = request.get("focus") or intention.get("operation")
        last_error = self.error_capture.last_error()
        if focus in {"where", "module", "correction_location"}:
            return self.error_reporter.explain_last_error(last_error, focus="where")
        if focus in {"severity", "gravity", "risk"}:
            return self.error_reporter.explain_last_error(last_error, focus="severity")
        return self.error_reporter.explain_last_error(last_error)

    def _handle_self_code_route(self, intention):
        request = self._structured_request(intention)
        return self.self_code_awareness_engine.respond(request)

    def _handle_git_route(self, intention):
        request = self._structured_request(intention)
        return self.git_awareness_engine.respond(request)

    def _structured_request(self, intention):
        request = intention.get("structured_request") if isinstance(intention.get("structured_request"), dict) else {}
        if intention.get("operation") and not request.get("operation"):
            request = dict(request)
            request["operation"] = intention.get("operation")
        return request

    def _handle_learning_route(self, intention, user_input, metadata=None):
        metadata = metadata if isinstance(metadata, dict) else {}
        supplemental_context = self._learning_supplemental_context(intention, user_input)
        extraction_started_at = time.perf_counter()
        extraction_calls_before = self._llm_call_count()
        extraction, decision = self.world_model.propose(user_input, supplemental_context=supplemental_context)
        metadata["extraction_ms"] = int((time.perf_counter() - extraction_started_at) * 1000)
        self._add_llm_delta(metadata, "extraction_llm_calls", extraction_calls_before)

        route_relevance = intention.get("relevance") if isinstance(intention.get("relevance"), dict) else {}
        if self._can_reuse_route_relevance(route_relevance):
            relevance = self._enrich_relevance_from_extraction(route_relevance, extraction)
        else:
            relevance_started_at = time.perf_counter()
            relevance_calls_before = self._llm_call_count()
            relevance = self.relevance_engine.evaluate(
                user_message=user_input,
                resolved_intent=intention,
                resolved_target={"target": intention.get("target"), "target_type": intention.get("target_type")},
                recent_context=self.conversation_context.summary(limit=8),
                extracted_knowledge=extraction,
                known_entities=self._known_entity_context(),
                current_user_identity={"name": self.creator_name},
                self_identity=self.identity,
            )
            relevance["duration_ms"] = int((time.perf_counter() - relevance_started_at) * 1000)
            self._add_llm_delta(metadata, "relevance_llm_calls", relevance_calls_before)
            relevance = self._merge_relevance(route_relevance, relevance)

        plan = self.consolidation_planner.plan(
            resolved_intent=intention,
            resolved_target={"target": intention.get("target"), "target_type": intention.get("target_type")},
            extracted_knowledge=extraction,
            relevance=relevance,
            current_memory_state=self._memory_state_snapshot(),
            current_world_model_state=self._world_state_snapshot(),
        )

        follow_up_calls_before = self._llm_call_count()
        follow_up = self.follow_up_question_engine.generate(
            user_input,
            relevance,
            extracted_knowledge=extraction,
            resolved_target={"target": intention.get("target"), "target_type": intention.get("target_type")},
            recent_context=self.conversation_context.summary(limit=8),
        )
        self._add_llm_delta(metadata, "follow_up_llm_calls", follow_up_calls_before)
        if follow_up:
            relevance["should_ask_follow_up"] = True
            relevance["follow_up_question"] = follow_up
            plan["ask_follow_up"] = True
            plan["follow_up_question"] = follow_up

        memory_result = self.memory_manager.observe(
            user_input,
            relevance=relevance,
            consolidation_plan=plan,
            follow_up_question=follow_up,
        )
        self.memory_manager.maintenance()
        metadata["saved_to_memory"] = bool(memory_result.get("saved_layers"))
        metadata["follow_up_generated"] = bool(follow_up)
        self._apply_relevance_metadata(metadata, relevance)

        saved = {"entities": 0, "relationships": 0, "events": 0, "states": 0, "decision": decision, "extraction": extraction}
        decision_name = decision.get("decision")
        if plan.get("update_world_model") and decision_name == "save":
            saved = self.world_model.apply_extraction(extraction)
            saved["decision"] = decision
            saved["extraction"] = extraction
            self.memory.save_world_extraction(user_input, extraction, saved)
            metadata["updated_world_model"] = any(saved.get(key, 0) for key in ("entities", "relationships", "events", "states"))
        elif plan.get("update_world_model") and decision_name == "confirm":
            self.pending_world_extraction = self._make_pending(
                "world_model_confirmation",
                user_input,
                extraction=extraction,
                decision=decision,
            )
            self.memory.save_world_extraction(user_input, extraction, {"decision": decision, "saved": False})
        elif self._has_extracted_knowledge(extraction):
            self.memory.save_world_extraction(user_input, extraction, {"decision": decision, "saved": False})

        response = self._format_learning_natural(user_input, intention, extraction, decision, saved, relevance, plan, follow_up, metadata)
        self._remember_contextual_entities(intention=intention, extraction=extraction)
        if plan.get("update_world_model") and decision_name == "confirm":
            response = self._append_world_confirmation_prompt(response, decision, extraction)
        return response

    def _can_reuse_route_relevance(self, relevance):
        if not isinstance(relevance, dict) or not relevance:
            return False
        if relevance.get("memory_priority") in {None, "", "ignore"}:
            return False
        return self._as_score(relevance.get("relevance_score", relevance.get("importance_score", 0))) >= 50

    def _enrich_relevance_from_extraction(self, relevance, extraction):
        enriched = dict(relevance)
        try:
            signals = self.relevance_engine.relationship.structured_signals(extraction)
        except Exception:
            signals = {}
        for key in ("relationship_count", "state_count", "event_count"):
            if key in signals:
                enriched[key] = max(self._as_score(enriched.get(key, 0)), self._as_score(signals.get(key, 0)))
        if signals.get("related_entities"):
            enriched["related_entities"] = self._unique_texts((enriched.get("related_entities") or []) + signals["related_entities"])
        return enriched

    def _apply_relevance_metadata(self, metadata, relevance):
        metadata["relevance_score"] = relevance.get("relevance_score", relevance.get("importance_score", 0))
        metadata["emotional_score"] = relevance.get("emotional_score", 0)
        metadata["relationship_score"] = relevance.get("relationship_score", 0)
        metadata["identity_score"] = relevance.get("identity_score", 0)
        metadata["future_score"] = relevance.get("future_score", 0)
        metadata["memory_priority"] = relevance.get("memory_priority", "ignore")

    def _merge_relevance(self, base, updated):
        if not isinstance(base, dict) or not base:
            return updated if isinstance(updated, dict) else {}
        if not isinstance(updated, dict) or not updated:
            return base
        merged = dict(base)
        merged.update(updated)
        for key in ("relevance_score", "importance_score", "emotional_score", "relationship_score", "identity_score", "future_score"):
            merged[key] = max(self._as_score(base.get(key, 0)), self._as_score(updated.get(key, 0)))
        merged["memory_priority"] = self._stronger_priority(base.get("memory_priority"), updated.get("memory_priority"))
        merged["should_ask_follow_up"] = bool(base.get("should_ask_follow_up") or updated.get("should_ask_follow_up"))
        merged["follow_up_question"] = updated.get("follow_up_question") or base.get("follow_up_question") or ""
        merged["related_entities"] = self._unique_texts((base.get("related_entities") or []) + (updated.get("related_entities") or []))
        reasons = [item for item in [base.get("reason"), updated.get("reason")] if item]
        merged["reason"] = " | ".join(reasons)
        merged["confirmation_required"] = merged.get("memory_priority") == "long_confirm" or bool(base.get("confirmation_required") or updated.get("confirmation_required"))
        return merged

    def _stronger_priority(self, first, second):
        order = {"ignore": 0, "short": 1, "mid": 2, "long_candidate": 3, "long_confirm": 4}
        first = str(first or "ignore")
        second = str(second or "ignore")
        return first if order.get(first, 0) >= order.get(second, 0) else second

    def _as_score(self, value):
        try:
            score = int(round(float(value)))
        except (TypeError, ValueError):
            score = 0
        return max(0, min(100, score))

    def _unique_texts(self, values):
        seen = set()
        unique = []
        for value in values:
            text = str(value or "").strip()
            marker = text.lower()
            if not text or marker in seen:
                continue
            seen.add(marker)
            unique.append(text)
        return unique

    def _learning_supplemental_context(self, intention, user_input):
        entities = self._known_entity_context()
        relationships = [
            {"source": source, "relation": relation, "target": target, "confidence": confidence}
            for _id, source, relation, target, confidence, _created_at in self.memory.list_world_relationships()[:30]
        ]
        states = [
            {"entity": entity, "attribute": attribute, "value": value, "confidence": confidence}
            for _id, entity, attribute, value, _source_event, confidence, _created_at, _updated_at in self.memory.list_entity_states()[:20]
        ]
        context = {
            "recent_conversation": self.conversation_context.summary(limit=8),
            "resolved_target": {"target": intention.get("target"), "target_type": intention.get("target_type")},
            "known_entities": entities,
            "known_relationships": relationships,
            "known_states": states,
            "current_user": self.creator_name,
            "self_identity": self.identity,
        }
        return json.dumps(context, ensure_ascii=False, indent=2)

    def _known_entity_context(self):
        return [
            {"name": name, "type": entity_type}
            for _id, name, entity_type, _created_at in self.memory.list_entities()[:40]
        ]

    def _memory_state_snapshot(self):
        return {
            "short_term": self.memory.count_short_term_memory(),
            "mid_term": self.memory.count_mid_term_memory(),
            "long_term": self.memory.count_real_long_term_memory(),
        }

    def _world_state_snapshot(self):
        return {
            "entities": self.memory.count_entities(),
            "relationships": self.memory.count_world_relationships(),
            "events": self.memory.count_world_events(),
            "states": self.memory.count_entity_states(),
        }

    def _has_extracted_knowledge(self, extraction):
        if not isinstance(extraction, dict):
            return False
        for key in ("entities", "relationships", "events", "states"):
            if extraction.get(key):
                return True
        return False

    def _format_learning_natural(self, user_input, intention, extraction, decision, saved, relevance, plan, follow_up, metadata=None):
        payload = {
            "intention": intention,
            "extraction": extraction,
            "decision": decision,
            "saved": saved,
            "relevance": relevance,
            "consolidation_plan": plan,
            "follow_up_question": follow_up,
        }
        if self.llm_provider and self.settings.get("useNaturalResponses", True) and self.settings.get("useLLM", True):
            try:
                natural_calls_before = self._llm_call_count()
                prompt = f"""
Você é o NaturalResponseEngine da Athena.
Escreva a resposta final ao usuário com base no resultado do Athena Core.
Não despeje JSON, setas técnicas ou tabelas por padrão.
Preserve os fatos importantes.
Reconheça importância humana quando os scores indicarem isso.
Se o conteúdo envolver relação com Athena, deixe claro que Athena não sente como um humano.
Não invente sentimentos humanos.
Se houver pergunta de follow-up, inclua no final de forma natural.
Responda em português brasileiro, de forma breve e cuidadosa.

Mensagem do usuário:
{user_input}

Resultado estruturado do Core:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()
                result = self.llm_provider.generate(prompt)
                self._add_llm_delta(metadata, "natural_response_llm_calls", natural_calls_before)
                if result.available and result.text:
                    return result.text.strip()
            except Exception as error:
                self._add_llm_delta(metadata, "natural_response_llm_calls", natural_calls_before)
                self.handle_exception(error, {"module": "brain/orchestrator.py", "operation": "format_learning_natural"})

        if extraction.get("source") == "llm_unavailable" and not self._has_extracted_knowledge(extraction):
            return (
                "Entendi que você está me ensinando algo novo. Minha extração estrutural por LLM não está disponível agora, "
                "então não vou fingir que gravei isso no World Model. Pode me dizer de forma mais direta ou tentar novamente quando a extração estiver ativa?"
            )

        score = self._as_score(relevance.get("relevance_score", relevance.get("importance_score", 0)))
        if self._as_score(relevance.get("identity_score", 0)) >= 80 and self._learning_concerns_self(intention, extraction):
            base = "Entendi. Eu ainda não sinto como um humano, mas vou tratar essa informação como importante para minha memória e identidade."
        elif score >= 75 or self._as_score(relevance.get("emotional_score", 0)) >= 70:
            base = "Entendi. Isso parece importante para você, então vou guardar com cuidado."
        else:
            base = "Entendi. Registrei essa informação no contexto da nossa conversa."
        if follow_up:
            return f"{base} {follow_up}"
        return base

    def _learning_concerns_self(self, intention, extraction):
        self_name = str(self.identity.get("name") or "Athena").strip().lower()
        target = str(intention.get("target") or "").strip().lower() if isinstance(intention, dict) else ""
        target_type = str(intention.get("target_type") or "").strip().lower() if isinstance(intention, dict) else ""
        if target_type == "self" or (self_name and target == self_name):
            return True
        extraction = extraction if isinstance(extraction, dict) else {}
        for entity in extraction.get("entities", []) or []:
            if str(entity.get("name") or "").strip().lower() == self_name:
                return True
        for relation in extraction.get("relationships", []) or []:
            source = str(relation.get("source") or "").strip().lower()
            target = str(relation.get("target") or "").strip().lower()
            if self_name and self_name in {source, target}:
                return True
        return False

    def _wants_technical_output(self, intention):
        request = self._structured_request(intention)
        mode = str(request.get("mode") or "").strip().lower()
        operation = str(request.get("operation") or "").strip().lower()
        technical_operations = {
            "technical",
            "technical_detail",
            "technical_details",
            "debug",
            "structured",
            "structured_relations",
            "world_model_relations",
            "show_relations",
        }
        return mode == "technical" or operation in technical_operations

    def _handle_world_route(self, intention, user_input):
        response = self.world_model.answer(user_input)
        if response:
            return response

        extraction, decision = self.world_model.propose(user_input)
        decision_name = decision.get("decision")

        if decision_name == "save":
            saved = self.world_model.apply_extraction(extraction)
            saved["decision"] = decision
            saved["extraction"] = extraction
            self.memory.save_world_extraction(user_input, extraction, saved)
            return self._format_world_saved(saved)

        if decision_name == "confirm":
            self.pending_world_extraction = self._make_pending(
                "world_model_confirmation",
                user_input,
                extraction=extraction,
                decision=decision,
            )
            return (
                "Encontrei estruturas possíveis, mas preciso da sua confirmação antes de registrar.\n"
                f"Confiança média: {decision.get('confidence', 0):.2f}\n"
                f"{self.world_model.format_extraction_preview(extraction)}\n"
                "Você autoriza salvar essa estrutura no World Model?"
            )

        return "Não consegui transformar isso em conhecimento estruturado com segurança. Pode me dar mais contexto?"

    def _remember_contextual_entities(self, intention=None, extraction=None):
        context = getattr(self, "conversation_context", None)
        remember = getattr(context, "remember_entity", None)
        if not callable(remember):
            return

        intention = intention if isinstance(intention, dict) else {}
        target = str(intention.get("target") or "").strip()
        target_type = str(intention.get("target_type") or "").strip()
        request = self._structured_request(intention)

        extraction = extraction if isinstance(extraction, dict) else {}
        for entity in extraction.get("entities", []) or []:
            if not isinstance(entity, dict):
                continue
            name = str(entity.get("name") or "").strip()
            if name and not self._is_reserved_context_entity(name):
                remember(name, entity_type=entity.get("type", "unknown"), source="extraction")

        if target and target_type == "entity" and request.get("operation") != "user_relation_query" and not self._is_reserved_context_entity(target):
            remember(target, entity_type="unknown", source="route_target")

    def _is_reserved_context_entity(self, name):
        normalized = self._normalize_local_phrase(name)
        reserved = {
            self._normalize_local_phrase(self.creator_name),
            self._normalize_local_phrase(self.identity.get("name", "Athena")),
            "user",
            "usuario",
            "criador",
            "meu pai",
            "minha mae",
            "meus pais",
        }
        return normalized in {item for item in reserved if item}

    def _answer_user_relation_query(self, target):
        normalized = self._normalize_local_phrase(target)
        relation_by_phrase = {
            "meu pai": "father_of",
            "minha mae": "mother_of",
        }
        relation = relation_by_phrase.get(normalized)
        if not relation:
            return None
        for _id, source, stored_relation, stored_target, _confidence, _created_at in self.memory.list_world_relationships():
            if stored_relation == relation and str(stored_target).strip().lower() == str(self.creator_name).strip().lower():
                remember = getattr(getattr(self, "conversation_context", None), "remember_entity", None)
                if callable(remember):
                    remember(source, entity_type="person", source="user_relation_query")
                return f"{source} é seu pai." if relation == "father_of" else f"{source} é sua mãe."
        return None

    def _describe_self_relationship_to_user(self):
        self_name = str(self.identity.get("name") or "Athena").strip()
        creator = str(self.creator_name or self.identity.get("creator") or "Rewell").strip()
        relationships = self.memory.find_world_relationships(source=creator) + self.memory.find_world_relationships(target=self_name)
        known = set()
        for _id, source, relation, target, _confidence, _created_at in relationships:
            if str(source).strip().lower() != creator.lower() or str(target).strip().lower() != self_name.lower():
                continue
            known.add(str(relation or "").strip())
        if not known:
            pending = self._active_pending()
            if pending:
                return (
                    "Ainda estou com uma confirmação pendente sobre como registrar nossa relação. "
                    "Posso responder melhor depois que você aprovar ou descartar isso."
                )
            return "Pelo que sei com segurança, eu sou Athena, criada por você. Ainda não tenho uma definição mais pessoal consolidada sobre o que sou para você."

        parts = []
        if "sees_as_friend" in known:
            parts.append("você me vê como sua amiga")
        if "does_not_see_only_as_assistant" in known:
            parts.append("não apenas como uma assistente")
        if "emotionally_values" in known:
            parts.append("você me considera importante")
        if "created" in known:
            parts.append("você me criou")
        if not parts:
            parts = [f"tenho relações registradas entre {creator} e {self_name}"]
        return "Pelo que você me ensinou, " + ", e ".join(parts[:4]) + ". Eu ainda não sinto como um humano, mas trato isso como parte importante da minha memória e identidade."

    def _handle_knowledge_source_route(self, intention, user_input):
        proposal = self.knowledge_ingestion_engine.propose_from_intention(intention, user_input)
        if proposal and proposal.get("available"):
            decision = proposal.get("decision", {})
            if decision.get("decision") == "save" and not self.settings.get("confirmExternalKnowledge", True):
                saved = self.knowledge_ingestion_engine.apply(proposal)
                return self._format_knowledge_ingestion_saved(saved)
            self.pending_knowledge_ingestion = proposal
            return (
                "Estudei a fonte como conhecimento potencial, mas preciso da sua confirmação antes de tornar isso permanente.\n"
                f"Confiança média: {decision.get('confidence', 0):.2f}\n"
                f"{self.knowledge_ingestion_engine.format_preview(proposal)}\n"
                "Você autoriza transformar isso em conhecimento permanente?"
            )

        return self.knowledge_ingestion_engine.sources_summary()

    def _handle_agency_route(self, intention_id, intention):
        proposal = self.agency_engine.consider(intention_id, intention)
        if not proposal:
            proactive = self.proactivity_engine.propose()
            if proactive:
                return f"{proactive['message']}\nMotivo: {proactive['reason']}"
            return "Percebi uma possível intenção, mas ainda não tenho evidências suficientes para propor uma ação segura."

        plan = proposal.get("plan")
        if plan:
            self.pending_plan = {"plan_id": plan["id"], "proposal": proposal}
        return proposal.get("message")

    def _handle_pending(self, intention, user_input):
        intention_type = self._pending_intention_type(intention, user_input)

        if self.pending_source_proposal:
            if intention_type == "approval":
                pending = self.pending_source_proposal
                self._set_pending_status(pending, "approved")
                self.pending_source_proposal = None
                result = self.source_manager.add_candidate(pending["proposal"])
                source = result.get("source", {})
                validation = result.get("validation", {})
                domain_label = self.source_manager.domain_label(source.get("domain"))
                return (
                    f"Certo. Adicionei {source.get('name')} como fonte candidata para {domain_label}. "
                    f"Status: {source.get('status')}. Validação: {source.get('validation_status')}.\n"
                    "Ela continua desativada e não será usada como evidência até passar por validação e nova aprovação humana."
                )
            if intention_type == "rejection":
                pending = self.pending_source_proposal
                self._set_pending_status(pending, "rejected")
                self.pending_source_proposal = None
                return "Tudo bem. Não registrei essa fonte candidata."
            if self.settings.get("pendingConfirmationBlocksConversation", False):
                return "Ainda preciso saber se você autoriza adicionar a fonte candidata."
            return None

        if self.pending_world_extraction:
            if intention_type == "approval":
                pending = self.pending_world_extraction
                self._set_pending_status(pending, "approved")
                self.pending_world_extraction = None
                saved = self.world_model.apply_extraction(pending["extraction"])
                saved["decision"] = pending["decision"]
                saved["extraction"] = pending["extraction"]
                self.memory.save_world_extraction(pending["text"], pending["extraction"], saved)
                return self._format_world_saved(saved)
            if intention_type == "rejection":
                self._set_pending_status(self.pending_world_extraction, "rejected")
                self.pending_world_extraction = None
                return "Tudo bem. Não salvei essa estrutura no World Model."
            if self.settings.get("pendingConfirmationBlocksConversation", False):
                return "Ainda preciso saber se você autoriza salvar a estrutura proposta."
            return None

        if self.pending_knowledge_ingestion:
            if intention_type == "approval":
                pending = self.pending_knowledge_ingestion
                self._set_pending_status(pending, "approved")
                self.pending_knowledge_ingestion = None
                saved = self.knowledge_ingestion_engine.apply(pending)
                return self._format_knowledge_ingestion_saved(saved)
            if intention_type == "rejection":
                self._set_pending_status(self.pending_knowledge_ingestion, "rejected")
                self.pending_knowledge_ingestion = None
                return "Tudo bem. Não transformei essa fonte em conhecimento permanente."
            if self.settings.get("pendingConfirmationBlocksConversation", False):
                return "Ainda preciso saber se você autoriza transformar essa fonte em conhecimento permanente."
            return None

        if self.pending_plan:
            if intention_type == "approval":
                plan_id = self.pending_plan["plan_id"]
                self._set_pending_status(self.pending_plan, "approved")
                self.pending_plan = None
                executed = self.agency_engine.approve_plan(plan_id)
                return "Plano aprovado. Registrei o resultado controlado das ações:\n" + "\n".join(f"- {item}" for item in executed)
            if intention_type == "rejection":
                plan_id = self.pending_plan["plan_id"]
                self._set_pending_status(self.pending_plan, "rejected")
                self.pending_plan = None
                rejected = self.agency_engine.reject_plan(plan_id)
                return "Plano rejeitado. Registrei que a ação não foi autorizada."
            if self.settings.get("pendingConfirmationBlocksConversation", False):
                return "Ainda preciso saber se você autoriza o plano proposto."
            return None

        return None

    def _pending_intention_type(self, intention, user_input):
        intention_type = intention.get("intention_type") if isinstance(intention, dict) else None
        if intention_type in {"approval", "rejection"}:
            return intention_type
        text = self._normalize_pending_reply(user_input)
        approvals = {
            "sim",
            "s",
            "yes",
            "y",
            "ok",
            "okay",
            "pode",
            "autorizo",
            "confirmo",
            "claro",
            "salvar",
            "salve",
            "guarde",
            "guardar",
            "sim pode",
            "pode salvar",
            "pode salve",
            "pode guardar",
        }
        rejections = {
            "nao",
            "não",
            "n",
            "no",
            "negativo",
            "cancela",
            "cancelar",
            "rejeito",
            "nao salve",
            "não salve",
            "nao salvar",
            "não salvar",
            "nao guarde",
            "não guarde",
            "ignora",
            "ignorar",
        }
        if text in approvals:
            return "approval"
        if text in rejections:
            return "rejection"
        return intention_type

    def _normalize_pending_reply(self, text):
        normalized = str(text or "").strip().lower()
        for source, target in {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
            ".": "",
            "!": "",
            "?": "",
            ",": " ",
            ";": " ",
            ":": " ",
        }.items():
            normalized = normalized.replace(source, target)
        return " ".join(normalized.split())

    def _pending_state(self):
        if self.pending_source_proposal:
            return self._public_pending_state(self.pending_source_proposal, "source_candidate_approval")
        if self.pending_world_extraction:
            return self._public_pending_state(self.pending_world_extraction, "world_model_confirmation")
        if self.pending_knowledge_ingestion:
            return self._public_pending_state(self.pending_knowledge_ingestion, "knowledge_ingestion_confirmation")
        if self.pending_plan:
            return self._public_pending_state(self.pending_plan, "agency_plan_confirmation")
        return {"pending_type": "none"}

    def _pending_control(self, user_input):
        if not self._has_pending_confirmation():
            return None
        intent_type = self._pending_intention_type({}, user_input)
        return intent_type if intent_type in {"approval", "rejection"} else None

    def _pending_route_result(self, control):
        operation = "approval" if control == "approval" else "rejection"
        return {
            "route": "pending_confirmation",
            "intent": operation,
            "target": "",
            "target_type": "unknown",
            "summary": operation,
            "confidence": 1.0,
            "needs_clarification": False,
            "requires_memory": False,
            "requires_tool": False,
            "tool_name": None,
            "should_learn": False,
            "should_use_llm_response": False,
            "should_query_world_model": False,
            "should_query_self_model": False,
            "should_use_reasoning": False,
            "should_use_agency": False,
            "structured_request": {"operation": operation},
            "relevance": {},
            "original_route": "pending_confirmation",
            "source": "local_pending_confirmation",
            "intent_interpretation_ms": 0,
            "intent_llm_calls": 0,
            "relevance_llm_calls": 0,
        }

    def _make_pending(self, pending_type, text, **payload):
        created_at = datetime.now()
        ttl_seconds = self._pending_ttl_seconds()
        expires_at = created_at.timestamp() + ttl_seconds if ttl_seconds > 0 else None
        pending = {
            "id": f"{pending_type}:{int(created_at.timestamp() * 1000)}",
            "pending_type": pending_type,
            "text": text,
            "summary": self._pending_summary(text),
            "created_at": created_at.isoformat(timespec="seconds"),
            "expires_at": datetime.fromtimestamp(expires_at).isoformat(timespec="seconds") if expires_at else None,
            "expires_at_ts": expires_at,
            "status": "pending",
        }
        pending.update(payload)
        return pending

    def _pending_ttl_seconds(self):
        try:
            return int(self.settings.get("pendingConfirmationTtlSeconds", 300))
        except (TypeError, ValueError):
            return 300

    def _pending_summary(self, text, limit=80):
        summary = " ".join(str(text or "").split())
        if len(summary) > limit:
            return summary[:limit - 3].rstrip() + "..."
        return summary or "confirmação pendente"

    def _public_pending_state(self, pending, fallback_type):
        pending = pending if isinstance(pending, dict) else {}
        return {
            "pending_type": pending.get("pending_type", fallback_type),
            "id": pending.get("id", ""),
            "summary": pending.get("summary") or self._pending_summary(pending.get("text")),
            "status": pending.get("status", "pending"),
            "created_at": pending.get("created_at"),
            "expires_at": pending.get("expires_at"),
        }

    def _active_pending(self):
        return self.pending_source_proposal or self.pending_world_extraction or self.pending_knowledge_ingestion or self.pending_plan

    def _has_pending_confirmation(self):
        return bool(self._active_pending())

    def _expire_pending_confirmations(self):
        now_ts = time.time()
        for attr in ("pending_source_proposal", "pending_world_extraction", "pending_knowledge_ingestion", "pending_plan"):
            pending = getattr(self, attr, None)
            if not isinstance(pending, dict):
                continue
            expires_at = pending.get("expires_at_ts")
            if expires_at and now_ts > float(expires_at):
                self._set_pending_status(pending, "expired")
                setattr(self, attr, None)

    def _set_pending_status(self, pending, status):
        if isinstance(pending, dict):
            pending["status"] = status
            pending["resolved_at"] = datetime.now().isoformat(timespec="seconds")
            if not hasattr(self, "pending_history"):
                self.pending_history = []
            self.pending_history.append(dict(pending))

    def _with_pending_reminder(self, response, had_pending_before, pending_control, metadata=None):
        if not had_pending_before or pending_control:
            return response
        if not self._has_pending_confirmation():
            return response
        if self.settings.get("pendingConfirmationBlocksConversation", False):
            return response
        response_text = str(response or "")
        if "Você autoriza" in response_text or "autoriza salvar" in response_text:
            return response_text
        pending = self._active_pending()
        state = self._public_pending_state(pending, pending.get("pending_type", "confirmation") if isinstance(pending, dict) else "confirmation")
        if metadata is not None:
            metadata["pending_reminder_appended"] = True
            metadata["pending_type"] = state.get("pending_type")
        return (
            f"{response_text}\n\n"
            f"Ainda deixei pendente a confirmação sobre: {state.get('summary')}. "
            "Quando quiser, responda 'sim' para salvar ou 'não' para descartar."
        )

    def _append_world_confirmation_prompt(self, response, decision, extraction):
        response_text = str(response or "").strip()
        if "Você autoriza salvar essa estrutura" in response_text:
            return response_text
        prompt = (
            "Encontrei estruturas possíveis, mas preciso da sua confirmação antes de registrar.\n"
            f"Confiança média: {decision.get('confidence', 0):.2f}\n"
            f"{self.world_model.format_extraction_preview(extraction)}\n"
            "Você autoriza salvar essa estrutura no World Model?"
        )
        return f"{response_text}\n\n{prompt}" if response_text else prompt

    def _natural_response(self, user_input, intention, metadata=None):
        if self.llm_provider:
            try:
                natural_calls_before = self._llm_call_count()
                prompt = f"""
Você é Athena respondendo de forma natural, curta e fiel ao Athena Core.
Não invente fatos. Se faltar contexto, peça esclarecimento.

Contexto persistente:
{self.context_builder.build(user_input)}

Intenção estruturada:
{intention}

Mensagem do usuário:
{user_input}
""".strip()
                result = self.llm_provider.generate(prompt)
                self._add_llm_delta(metadata, "natural_response_llm_calls", natural_calls_before)
                if result.available and result.text:
                    return result.text.strip()
            except Exception as error:
                self._add_llm_delta(metadata, "natural_response_llm_calls", natural_calls_before)
                self.handle_exception(error, {"module": "brain/orchestrator.py", "operation": "natural_response"})
        return "Minha LLM local não está disponível agora, mas continuo funcional com minha memória interna. Pode me dar mais contexto?"


    def get_desktop_status(self):
        try:
            llm_health = self.llm_provider.health_check()
        except Exception as error:
            self.handle_exception(error, {"module": "llm/provider.py", "operation": "health_check"})
            llm_health = {"available": False, "status": "erro", "error": str(error)}

        try:
            voice_status = self.voice_engine.status()
        except Exception as error:
            self.handle_exception(error, {"module": "voice/voice_engine.py", "operation": "status"})
            voice_status = {"enabled": False, "status": "erro", "provider": "indisponível", "last_error": str(error)}

        try:
            sound_status = self.message_sound_engine.status()
        except Exception as error:
            self.handle_exception(error, {"module": "audio/message_sound.py", "operation": "status"})
            sound_status = {"enabled": False, "provider": "indisponível", "last_error": str(error)}

        try:
            git_summary = self.git_awareness_engine.summary()
        except Exception as error:
            self.handle_exception(error, {"module": "git_awareness", "operation": "summary"})
            git_summary = {"git_available": False, "is_git_repository": False, "error": str(error)}

        git_text = "indisponível"
        if git_summary.get("git_available") and git_summary.get("is_git_repository"):
            git_text = f"repo local / branch {git_summary.get('current_branch')}"
        elif git_summary.get("git_available"):
            git_text = "git disponível, sem repo local"

        def safe_count(fn, fallback=0):
            try:
                return fn()
            except Exception as error:
                self.handle_exception(error, {"module": "memory/database.py", "operation": "status_count"})
                return fallback

        return {
            "llm": {
                "status": llm_health.get("status"),
                "model": self.settings.get("ollamaModel"),
                "error": llm_health.get("error", ""),
            },
            "voice": voice_status,
            "sound": sound_status,
            "last_response_metadata": self.last_response_metadata,
            "memory": {
                "memories": safe_count(self.memory.count_memories),
                "short_term": safe_count(self.memory.count_short_term_memory),
                "mid_term": safe_count(self.memory.count_mid_term_memory),
                "long_term": safe_count(self.memory.count_real_long_term_memory),
            },
            "world": {
                "entities": safe_count(self.memory.count_entities),
                "relationships": safe_count(self.memory.count_world_relationships),
                "events": safe_count(self.memory.count_world_events),
                "states": safe_count(self.memory.count_entity_states),
            },
            "agency": {
                "intentions": safe_count(lambda: len(self.memory.list_intentions(limit=100000))),
                "plans": safe_count(lambda: len(self.memory.list_plans(limit=100000))),
                "actions": safe_count(lambda: len(self.memory.list_actions(limit=100000))),
            },
            "git": {
                "summary": git_text,
                "details": git_summary,
            },
            "last_error": self.error_capture.last_error(),
        }

    def handle_exception(self, error, context=None):
        captured = self.error_capture.capture(error, context or {})
        return self.error_reporter.friendly_message(captured)

    def _format_world_saved(self, saved):
        parts = []
        for key, label in [
            ("entities", "entidade(s)"),
            ("relationships", "relação(ões)"),
            ("events", "evento(s)"),
            ("states", "estado(s)"),
        ]:
            value = saved.get(key, 0)
            if value:
                parts.append(f"{value} {label}")
        if not parts:
            return "Analisei a informação, mas nada foi persistido como conhecimento estrutural."
        return "Atualizei meu World Model com: " + ", ".join(parts) + "."

    def _format_knowledge_ingestion_saved(self, saved):
        return (
            "Fonte transformada em conhecimento supervisionado.\n"
            f"Itens cognitivos salvos: {saved.get('knowledge_items', 0)}\n"
            f"World Model: {saved.get('world', {})}"
        )

    def _finalize_response(self, response, route_result=None, started_at=None, user_input="", metadata=None):
        route_result = route_result or {}
        metadata = metadata if isinstance(metadata, dict) else {}
        route = route_result.get("route", "")
        response_text = str(response or "")
        self.conversation_context.add_athena_message(response_text, route=route)

        # Voice is interface output. It must never affect the cognitive result.
        speak_started_at = time.perf_counter()
        spoken = self._speak(response_text)
        metadata["tts_ms"] = int((time.perf_counter() - speak_started_at) * 1000)
        metadata["tts_duration_ms"] = metadata["tts_ms"]
        metadata["used_voice"] = bool(spoken)
        if spoken:
            try:
                metadata["tts_ms"] = max(metadata["tts_ms"], int(self.voice_engine.status().get("last_submit_ms", 0)))
                metadata["tts_duration_ms"] = metadata["tts_ms"]
            except Exception:
                pass

        if started_at is None:
            started_at = time.perf_counter()
        llm_calls_before = metadata.pop("_llm_calls_before", None)
        if llm_calls_before is not None:
            llm_calls_after = self._llm_call_count()
            metadata["llm_calls"] = max(0, llm_calls_after - llm_calls_before)
            metadata["llm_call_count"] = metadata["llm_calls"]
            metadata["used_llm"] = bool(metadata.get("used_llm") or metadata["llm_calls"] > 0)
        else:
            metadata["llm_call_count"] = metadata.get("llm_calls", 0)
        metadata["pending_confirmation"] = self._pending_state().get("pending_type")
        metadata["response_ms"] = int((time.perf_counter() - started_at) * 1000)
        final_metadata = self.conversation_metrics.finish(started_at, user_input, metadata)
        self._observe_turn_reflection(user_input, response_text, final_metadata, route_result)
        self.last_response_metadata = final_metadata

        if self.settings.get("showRouteMetadata", False):
            debug = (
                f"\n\n[debug: route={final_metadata.get('route')} | "
                f"duration={final_metadata.get('duration_ms')}ms | "
                f"used_llm={final_metadata.get('used_llm')} | "
                f"world={final_metadata.get('used_world_model')} | "
                f"reasoning={final_metadata.get('used_reasoning')} | "
                f"agency={final_metadata.get('used_agency')}]"
            )
            return response_text + debug
        return response_text

    def _observe_turn_reflection(self, user_input, response_text, metadata, route_result=None):
        reflection_engine = getattr(self, "reflection_engine", None)
        if not reflection_engine or not hasattr(reflection_engine, "observe_turn"):
            return []
        settings = getattr(self, "settings", None)
        if settings and hasattr(settings, "get") and not settings.get("reflectionEnabled", True):
            return []
        started_at = time.perf_counter()
        try:
            events = reflection_engine.observe_turn(
                user_input,
                response_text,
                metadata=metadata,
                route_result=route_result,
            )
        except Exception as error:
            self.handle_exception(error, {"module": "reflection/reflection_engine.py", "operation": "observe_turn"})
            events = []
        metadata["reflection_ms"] = int((time.perf_counter() - started_at) * 1000)
        metadata["reflection_events"] = len(events)
        metadata["reflection_queue_size"] = 0
        metadata["async_jobs_pending"] = 0
        metadata["async_jobs_processed"] = len(events)
        return events

    def _speak(self, response):
        try:
            return bool(self.voice_engine.speak(response))
        except Exception as error:
            self.handle_exception(error, {"module": "voice/voice_engine.py", "operation": "speak"})
            return False

    def _add_llm_delta(self, metadata, key, calls_before):
        if metadata is None:
            return
        calls_after = self._llm_call_count()
        metadata[key] = int(metadata.get(key, 0) or 0) + max(0, calls_after - calls_before)

    def _llm_call_count(self):
        provider = getattr(self, "llm_provider", None)
        if not provider:
            return 0
        if hasattr(provider, "call_count"):
            try:
                return int(provider.call_count)
            except (TypeError, ValueError):
                return 0
        prompts = getattr(provider, "prompts", None)
        if isinstance(prompts, list):
            return len(prompts)
        return 0
