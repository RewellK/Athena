import json

from agency.action_engine import ActionEngine
from agency.agency_engine import AgencyEngine
from agency.goal_engine import GoalEngine
from agency.intention_engine import IntentionEngine
from agency.proactivity_engine import ProactivityEngine
from agency.tool_registry import ToolRegistry
from bootstrap import AthenaBootstrap
from core.context_builder import ContextBuilder
from core.logger import AthenaLogger
from core.settings import Settings
from curiosity.curiosity_engine import CuriosityEngine
from forgetting_engine import ForgettingEngine
from git_awareness.git_awareness_engine import GitAwarenessEngine
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
    V11 Orchestrator lockdown.

    The Orchestrator does not interpret language, intent, or meaning.
    It receives text, asks IntentionEngine for structure, delegates to modules,
    and returns the selected module response.
    """

    def __init__(self):
        self.logger = AthenaLogger()
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

        self.pending_world_extraction = None
        self.pending_knowledge_ingestion = None
        self.pending_plan = None

    def chat(self, user_input):
        self.memory.save_memory("conversation", user_input)
        self.memory_manager.observe(user_input)
        self.memory_manager.maintenance()

        pending_state = self._pending_state()
        intention = self.intention_engine.interpret(user_input, pending_state=pending_state)
        intention_id = self.memory.save_intention(
            user_input,
            intention,
            confidence=intention.get("confidence", 0.0),
            status="observed",
        )

        pending_response = self._handle_pending(intention, user_input)
        if pending_response:
            return self._speak(pending_response)

        if intention.get("needs_clarification") or intention.get("confidence", 0.0) < 0.50:
            return self._speak("Não consegui interpretar isso com segurança. Pode me explicar melhor?")

        response = self._delegate(intention_id, intention, user_input)
        if response:
            return self._speak(response)

        fallback = self._natural_response(user_input, intention)
        return self._speak(fallback)

    def _delegate(self, intention_id, intention, user_input):
        route = intention.get("route")

        if route == "knowledge_sources":
            return self._handle_knowledge_source_route(intention, user_input)

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
        return "Minha LLM local não está disponível agora, mas continuo funcional com minha memória interna. Pode me dar mais contexto?"


    def get_desktop_status(self):
        llm_health = self.llm_provider.health_check()
        voice_status = self.voice_engine.status()
        git_summary = self.git_awareness_engine.summary()
        git_text = "indisponível"
        if git_summary.get("git_available") and git_summary.get("is_git_repository"):
            git_text = f"repo local / branch {git_summary.get('current_branch')}"
        elif git_summary.get("git_available"):
            git_text = "git disponível, sem repo local"
        return {
            "llm": {
                "status": llm_health.get("status"),
                "model": self.settings.get("ollamaModel"),
                "error": llm_health.get("error", ""),
            },
            "voice": voice_status,
            "memory": {
                "memories": self.memory.count_memories(),
                "short_term": self.memory.count_short_term_memory(),
                "mid_term": self.memory.count_mid_term_memory(),
                "long_term": self.memory.count_real_long_term_memory(),
            },
            "world": {
                "entities": self.memory.count_entities(),
                "relationships": self.memory.count_world_relationships(),
                "events": self.memory.count_world_events(),
                "states": self.memory.count_entity_states(),
            },
            "agency": {
                "intentions": len(self.memory.list_intentions(limit=100000)),
                "plans": len(self.memory.list_plans(limit=100000)),
                "actions": len(self.memory.list_actions(limit=100000)),
            },
            "git": {
                "summary": git_text,
                "details": git_summary,
            },
        }

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

    def _speak(self, response):
        self.voice_engine.speak(response)
        return response
