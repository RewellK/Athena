import json
import time

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
from reasoning.reasoning_engine import ReasoningEngine
from reflection.reflection_engine import ReflectionEngine
from self_model.self_model import SelfModel
from self_code_awareness.self_code_awareness_engine import SelfCodeAwarenessEngine
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
        self.conversation_router = ConversationRouter(self.llm_provider, self.context_builder, self.logger, identity=self.identity, settings=self.settings)
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

        self.pending_world_extraction = None
        self.pending_knowledge_ingestion = None
        self.pending_plan = None

    def chat(self, user_input):
        try:
            return self._chat_impl(user_input)
        except Exception as error:
            return self.handle_exception(error, {"module": "brain/orchestrator.py", "operation": "chat"})

    def _chat_impl(self, user_input):
        started_at = self.conversation_metrics.start()
        self.message_sound_engine.play_received()
        self.conversation_context.add_user_message(user_input)

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

        metadata = {
            "route": intention.get("route"),
            "intent": intention.get("intent"),
            "target": intention.get("target", ""),
            "used_llm": route_result.get("source", "").startswith("llm"),
            "used_world_model": False,
            "used_reasoning": False,
            "used_agency": False,
            "used_voice": False,
            "used_sound": self.settings.get("messageReceivedSoundEnabled", True),
            "intent_interpretation_ms": route_result.get("intent_interpretation_ms", 0),
        }

        pending_response = self._handle_pending(intention, user_input)
        if pending_response:
            return self._finalize_response(pending_response, route_result, started_at, user_input, metadata)

        response = self._delegate_conversation_route(intention_id, intention, user_input, metadata)
        if response:
            return self._finalize_response(response, route_result, started_at, user_input, metadata)

        fallback = self.conversation_engine.respond(user_input, route_result, self.conversation_context)
        return self._finalize_response(fallback, route_result, started_at, user_input, metadata)

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
            return self.identity_engine.respond(user_input, operation=operation, target=intention.get("target"))

        if route == "question_about_user":
            return self._handle_question_about_user(intention, user_input, metadata)

        if route == "capability":
            technical = intention.get("intent") == "technical_capability" or self._structured_request(intention).get("operation") == "technical_modules"
            return self.capability_engine.respond(technical=technical)

        if route == "technical_capability":
            return self.capability_engine.respond(technical=True)

        if route == "self_status":
            return self.self_status_engine.respond()

        if route == "error_query":
            return self._handle_error_awareness_route(intention)

        if route == "memory_query":
            return self.reflection_engine.respond(user_input)

        if route == "world_query":
            metadata["used_world_model"] = True
            response = self.world_model.answer(user_input)
            return response or self._natural_response(user_input, intention)

        if route == "reasoning":
            metadata["used_reasoning"] = True
            return self.reasoning_engine.respond(user_input)

        if route == "learning":
            metadata["used_world_model"] = True
            self.memory.save_memory("conversation", user_input)
            self.memory_manager.observe(user_input)
            self.memory_manager.maintenance()
            return self._handle_world_route(intention, user_input)

        if route == "agency":
            metadata["used_agency"] = True
            return self._handle_agency_route(intention_id, intention)

        if route == "system":
            return self._handle_system_route(intention)

        if intention.get("needs_clarification") or intention.get("confidence", 0.0) < 0.45:
            return "Não entendi com segurança o que você quer agora. Pode me explicar de outro jeito?"

        return self._delegate(intention_id, intention, user_input)

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
            rows = self.memory.find_entities(name_fragment=target)
            if rows:
                lines = [f"Encontrei {rows[0][1]} no meu World Model como {rows[0][2]}."]
                relationships = self.memory.find_world_relationships(source=rows[0][1]) + self.memory.find_world_relationships(target=rows[0][1])
                if relationships:
                    lines.append("Relações conhecidas:")
                    for _id, source, relation, related_target, confidence, _created_at in relationships[:6]:
                        lines.append(f"- {source} -> {relation} -> {related_target} | confiança={confidence}")
                return "\n".join(lines)
            return f"Ainda não tenho informações suficientes sobre {target}."

        return "Ainda não tenho informações suficientes sobre essa pessoa ou entidade."

    def _handle_system_route(self, intention):
        request = self._structured_request(intention)
        subsystem = request.get("subsystem")
        operation = request.get("operation") or intention.get("operation")

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
            return self.reasoning_engine.respond(user_input)

        if route == "reflection":
            return self.reflection_engine.respond(user_input)

        if route == "self_model":
            return self.self_model.respond(user_input)

        if route == "curiosity":
            return self.curiosity_engine.respond(user_input)

        if route == "agency" or intention.get("requires_action"):
            return self._handle_agency_route(intention_id, intention)

        if intention.get("intention_type") == "knowledge_input":
            return self._handle_world_route(intention, user_input)

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
            return self.reasoning_engine.respond(user_input)

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
            self.pending_world_extraction = {"text": user_input, "extraction": extraction, "decision": decision}
            return (
                "Encontrei estruturas possíveis, mas preciso da sua confirmação antes de registrar.\n"
                f"Confiança média: {decision.get('confidence', 0):.2f}\n"
                f"{self.world_model.format_extraction_preview(extraction)}\n"
                "Você autoriza salvar essa estrutura no World Model?"
            )

        return "Não consegui transformar isso em conhecimento estruturado com segurança. Pode me dar mais contexto?"

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
        intention_type = intention.get("intention_type")

        if self.pending_world_extraction:
            if intention_type == "approval":
                pending = self.pending_world_extraction
                self.pending_world_extraction = None
                saved = self.world_model.apply_extraction(pending["extraction"])
                saved["decision"] = pending["decision"]
                saved["extraction"] = pending["extraction"]
                self.memory.save_world_extraction(pending["text"], pending["extraction"], saved)
                return self._format_world_saved(saved)
            if intention_type == "rejection":
                self.pending_world_extraction = None
                return "Tudo bem. Não salvei essa estrutura no World Model."
            return "Ainda preciso saber se você autoriza salvar a estrutura proposta."

        if self.pending_knowledge_ingestion:
            if intention_type == "approval":
                pending = self.pending_knowledge_ingestion
                self.pending_knowledge_ingestion = None
                saved = self.knowledge_ingestion_engine.apply(pending)
                return self._format_knowledge_ingestion_saved(saved)
            if intention_type == "rejection":
                self.pending_knowledge_ingestion = None
                return "Tudo bem. Não transformei essa fonte em conhecimento permanente."
            return "Ainda preciso saber se você autoriza transformar essa fonte em conhecimento permanente."

        if self.pending_plan:
            if intention_type == "approval":
                plan_id = self.pending_plan["plan_id"]
                self.pending_plan = None
                executed = self.agency_engine.approve_plan(plan_id)
                return "Plano aprovado. Registrei o resultado controlado das ações:\n" + "\n".join(f"- {item}" for item in executed)
            if intention_type == "rejection":
                plan_id = self.pending_plan["plan_id"]
                self.pending_plan = None
                rejected = self.agency_engine.reject_plan(plan_id)
                return "Plano rejeitado. Registrei que a ação não foi autorizada."
            return "Ainda preciso saber se você autoriza o plano proposto."

        return None

    def _pending_state(self):
        if self.pending_world_extraction:
            return {"pending_type": "world_model_confirmation"}
        if self.pending_knowledge_ingestion:
            return {"pending_type": "knowledge_ingestion_confirmation"}
        if self.pending_plan:
            return {"pending_type": "agency_plan_confirmation"}
        return {"pending_type": "none"}

    def _natural_response(self, user_input, intention):
        if self.llm_provider:
            try:
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
                if result.available and result.text:
                    return result.text.strip()
            except Exception as error:
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
        spoken = self._speak(response_text)
        metadata["used_voice"] = bool(spoken)

        if started_at is None:
            started_at = time.perf_counter()
        final_metadata = self.conversation_metrics.finish(started_at, user_input, metadata)
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

    def _speak(self, response):
        try:
            return bool(self.voice_engine.speak(response))
        except Exception as error:
            self.handle_exception(error, {"module": "voice/voice_engine.py", "operation": "speak"})
            return False
