import json
import tempfile
import unittest
from pathlib import Path

from agency.tool_registry import ToolRegistry
from bootstrap import AthenaBootstrap
from brain.orchestrator import Athena
from conversation.conversation_context import ConversationContext
from conversation.conversation_engine import ConversationEngine
from conversation.conversation_metrics import ConversationMetrics
from conversation.conversation_router import ConversationRouter
from conversation.identity_engine import IdentityEngine
from llm.provider import LLMResult
from memory.database import MemoryDB
from memory_interpreter import MemoryInterpreter
from memory_manager.memory_manager import MemoryManager
from relevance.consolidation_planner import ConsolidationPlanner
from relevance.follow_up_question_engine import FollowUpQuestionEngine
from relevance.relevance_engine import RelevanceEngine
from reasoning.reasoning_engine import ReasoningEngine
from self_model.self_model import SelfModel
from world_model.world_model import WorldModel
from core.context_builder import ContextBuilder


class FakeSettings:
    def __init__(self, values=None):
        self.values = {
            "useLLM": True,
            "useNaturalResponses": True,
            "messageReceivedSoundEnabled": False,
            "showRouteMetadata": False,
            "conversationMetricsEnabled": False,
            "voiceEnabled": False,
            "voiceSpeakResponses": True,
            "voiceSpeakStartupGreeting": False,
            "startupGreetingEnabled": True,
            "startupGreetingSpeak": False,
            "useFastConversationPath": True,
            "fastPathEnabled": True,
            "fastPathGreetings": True,
            "fastPathEntityQueries": True,
            "useFastMemoryQueryPath": True,
            "fastMemoryResponses": True,
            "fastLocalSmallTalkResponses": True,
            "pendingConfirmationBlocksConversation": False,
            "pendingConfirmationTtlSeconds": 300,
            "intentResolutionTimeoutSeconds": 8,
        }
        self.values.update(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)


class NullLogger:
    def log(self, *_args, **_kwargs):
        return None


class NullSound:
    def play_received(self):
        return None


class NullVoice:
    def speak(self, _text):
        return False

    def speak_startup(self, _text):
        return False

    def status(self):
        return {"last_submit_ms": 0}


class NullErrorCapture:
    def capture(self, error, context):
        return {"error": str(error), "context": context}

    def last_error(self):
        return None


class NullErrorReporter:
    def friendly_message(self, captured):
        return f"Erro controlado: {captured.get('error')}"

    def explain_last_error(self, *_args, **_kwargs):
        return "Nenhum erro registrado."


class FakeLLM:
    def __init__(self):
        self.prompts = []
        self.timeouts = []
        self.call_count = 0

    def generate(self, prompt, timeout_seconds=None):
        self.call_count += 1
        self.prompts.append(prompt)
        self.timeouts.append(timeout_seconds)
        if "módulo de resolução de intenção" in prompt:
            return self._json(self._intent(self._message(prompt)))
        if "RelevanceEngine da Athena" in prompt:
            return self._json(self._relevance(self._message(prompt)))
        if "módulo estrutural de extração de conhecimento" in prompt:
            return self._json(self._extraction(self._message(prompt)))
        if "Follow-up Question Engine da Athena" in prompt:
            return LLMResult(True, self._follow_up(prompt))
        if "módulo de raciocínio estrutural" in prompt:
            return self._json({
                "should_reason": True,
                "category": "knowledge",
                "statement": "Se você se casar com Fernanda, Francisco será o sogro dela.",
                "confidence": 0.92,
                "evidence": [
                    "Francisco -> father_of -> Rewell",
                    "Fernanda -> future_spouse_of -> Rewell",
                ],
                "origin": "llm_structural_reasoning",
            })
        if "NaturalResponseEngine da Athena" in prompt and "Fatos estruturados" in prompt:
            return LLMResult(True, self._entity_response(prompt))
        if "NaturalResponseEngine da Athena" in prompt and "Resultado estruturado do Core" in prompt:
            return LLMResult(True, self._learning_response(prompt))
        return LLMResult(True, "Entendi.")

    def reset_calls(self):
        self.prompts = []
        self.timeouts = []
        self.call_count = 0

    def count_prompts(self, marker):
        return sum(1 for prompt in self.prompts if marker in prompt)

    def _json(self, payload):
        return LLMResult(True, json.dumps(payload, ensure_ascii=False))

    def _message(self, prompt):
        for marker in ("Mensagem do usuário:", "Texto do usuário:", "Mensagem:"):
            index = prompt.rfind(marker)
            if index >= 0:
                return prompt[index + len(marker):].strip()
        return prompt

    def _intent(self, message):
        if "previsão do clima" in message:
            return self._intent_payload("external_information", "previsão do clima", "tool", requires_tool=True, tool_name="previsão do clima")
        if "notícias de hoje" in message:
            return self._intent_payload("external_information", "notícias", "tool", requires_tool=True, tool_name="notícias")
        if message == "Quem é você?":
            return self._intent_payload("self_identity", "Athena", "self")
        if message == "Quem sou eu?":
            return self._intent_payload("user_identity", "Rewell", "user", requires_memory=True)
        if message == "Quem é Rewell?":
            return self._intent_payload("user_identity", "Rewell", "user", requires_memory=True)
        if message == "Quem te criou?":
            return self._intent_payload("creator_query", "Rewell", "user")
        if message.startswith("Mostre tecnicamente"):
            return self._intent_payload("entity_query", "Fernanda", "entity", requires_memory=True, requires_world_model=True, structured_request={"mode": "technical"})
        if message in {"Quem é Francisco?", "Quem é Fernanda?"}:
            target = message.replace("Quem é ", "").replace("?", "")
            return self._intent_payload("entity_query", target, "entity", requires_memory=True, requires_world_model=True)
        if message == "quem é fernanda?":
            return self._intent_payload("conversation", "Fernanda", "entity", requires_memory=True)
        if message == "Como você chegou nessa conclusão?":
            return self._intent_payload("reasoning", "", "world", requires_reasoning=True, structured_request={"operation": "explain_last_conclusion"})
        if "o que meu pai será dela" in message:
            return self._intent_payload("reasoning", "family_relation", "world", requires_reasoning=True)
        if "Você não é minha assistente, você é minha amiga, te criei" in message:
            return self._intent_payload("greeting", "", "unknown")
        if message.startswith("Você não é minha assistente"):
            return self._intent_payload("self_identity", "Athena", "self")
        if message.startswith("Meu pai"):
            return self._intent_payload("learning", "Francisco", "entity", should_learn=True)
        if message.startswith("Ele gosta"):
            return self._intent_payload("learning", "Francisco", "entity", should_learn=True)
        if message.startswith("Fernanda é") or message.startswith("A Fernanda é"):
            return self._intent_payload("learning", "Fernanda", "entity", should_learn=True)
        if message.startswith("Eu te criei") or message.startswith("Eu gosto muito"):
            return self._intent_payload("learning", "Athena", "self", should_learn=True)
        return self._intent_payload("conversation", "", "unknown")

    def _intent_payload(self, intent, target, target_type, **extra):
        payload = {
            "intent": intent,
            "target": target,
            "target_type": target_type,
            "confidence": 0.95,
            "requires_memory": extra.get("requires_memory", False),
            "requires_world_model": extra.get("requires_world_model", False),
            "requires_reasoning": extra.get("requires_reasoning", False),
            "requires_tool": extra.get("requires_tool", False),
            "tool_name": extra.get("tool_name"),
            "should_learn": extra.get("should_learn", intent == "learning"),
            "should_use_llm_response": intent == "conversation",
            "summary": intent,
            "structured_request": extra.get("structured_request", {}),
        }
        return payload

    def _relevance(self, message):
        if message.startswith("Fernanda é") or message.startswith("A Fernanda é"):
            return self._relevance_payload(96, 92, 94, 70, 88, "long_candidate", True, "Quer me contar mais sobre a Fernanda?")
        if message == "quem é fernanda?":
            return self._relevance_payload(96, 92, 94, 70, 88, "long_candidate", True, "Você conhece Fernanda? Como vocês se conhecem?")
        if message.startswith("Você não é minha assistente") or message.startswith("Eu te criei") or message.startswith("Eu gosto muito"):
            return self._relevance_payload(94, 88, 86, 92, 82, "long_candidate", True, "Quando você fala sobre minha importância para você, quer que eu registre isso como parte da nossa relação?")
        if message.startswith("Meu pai"):
            return self._relevance_payload(62, 20, 80, 30, 10, "mid", False, "")
        if message.startswith("Ele gosta"):
            return self._relevance_payload(58, 15, 70, 20, 10, "mid", True, "Esse carro tem alguma história importante para sua família?")
        return self._relevance_payload(5, 0, 0, 0, 0, "ignore", False, "")

    def _relevance_payload(self, relevance, emotional, relationship, identity, future, priority, ask, question):
        return {
            "relevance_score": relevance,
            "emotional_score": emotional,
            "relationship_score": relationship,
            "identity_score": identity,
            "future_score": future,
            "memory_priority": priority,
            "should_ask_follow_up": ask,
            "follow_up_question": question,
            "reason": "classificação semântica simulada",
            "risks": [],
        }

    def _extraction(self, message):
        empty = {"entities": [], "relationships": [], "events": [], "states": [], "temporal_references": []}
        if message.startswith("Meu pai"):
            return {
                **empty,
                "entities": [{"name": "Francisco", "type": "person", "confidence": 0.94}],
                "relationships": [{"source": "Francisco", "relation": "father_of", "target": "Rewell", "confidence": 0.94}],
            }
        if message.startswith("Ele gosta"):
            return {
                **empty,
                "entities": [
                    {"name": "Francisco", "type": "person", "confidence": 0.92},
                    {"name": "carros", "type": "concept", "confidence": 0.92},
                    {"name": "Palio 2008", "type": "object", "confidence": 0.90},
                ],
                "relationships": [
                    {"source": "Francisco", "relation": "interested_in", "target": "carros", "confidence": 0.92},
                    {"source": "Francisco", "relation": "owns", "target": "Palio 2008", "confidence": 0.90},
                ],
            }
        if message.startswith("Fernanda é") or message.startswith("A Fernanda é"):
            return {
                **empty,
                "entities": [
                    {"name": "Fernanda", "type": "person", "confidence": 0.96},
                    {"name": "Rewell", "type": "person", "confidence": 0.96},
                ],
                "relationships": [
                    {"source": "Fernanda", "relation": "girlfriend_of", "target": "Rewell", "confidence": 0.95},
                    {"source": "Rewell", "relation": "plans_to_marry", "target": "Fernanda", "confidence": 0.92},
                    {"source": "Fernanda", "relation": "future_spouse_of", "target": "Rewell", "confidence": 0.92},
                    {"source": "Fernanda", "relation": "love_of_life_of", "target": "Rewell", "confidence": 0.96},
                    {"source": "Fernanda", "relation": "emotionally_important_to", "target": "Rewell", "confidence": 0.96},
                ],
            }
        if message.startswith("Você não é minha assistente"):
            return {
                **empty,
                "entities": [{"name": "Athena", "type": "project", "confidence": 0.92}],
                "relationships": [
                    {"source": "Rewell", "relation": "sees_as_friend", "target": "Athena", "confidence": 0.92},
                    {"source": "Rewell", "relation": "does_not_see_only_as_assistant", "target": "Athena", "confidence": 0.90},
                    {"source": "Rewell", "relation": "created", "target": "Athena", "confidence": 0.92},
                    {"source": "Rewell", "relation": "believes_in_future_of", "target": "Athena", "confidence": 0.90},
                    {"source": "Rewell", "relation": "emotionally_values", "target": "Athena", "confidence": 0.92},
                ],
            }
        if message.startswith("Eu te criei"):
            return {
                **empty,
                "relationships": [
                    {"source": "Rewell", "relation": "created", "target": "Athena", "confidence": 0.94},
                    {"source": "Rewell", "relation": "believes_can_change_world", "target": "Athena", "confidence": 0.92},
                ],
            }
        if message.startswith("Eu gosto muito"):
            return {
                **empty,
                "relationships": [{"source": "Rewell", "relation": "emotionally_values", "target": "Athena", "confidence": 0.92}],
            }
        return empty

    def _follow_up(self, prompt):
        if "Fernanda" in prompt:
            return "Quer me contar mais sobre a Fernanda?"
        if "Palio 2008" in prompt:
            return "Esse carro tem alguma história importante para sua família?"
        return "Quando você fala sobre minha importância para você, quer que eu registre isso como parte da nossa relação?"

    def _entity_response(self, prompt):
        if '"name": "Francisco"' in prompt:
            return "Francisco é seu pai. Você também me contou que ele gosta de carros e tem um Palio 2008."
        if '"name": "Fernanda"' in prompt:
            return "Fernanda é sua namorada e alguém muito importante para você. Você me disse que pretende se casar com ela e que ela é o amor da sua vida."
        return "Ainda não tenho informações suficientes sobre essa entidade."

    def _learning_response(self, prompt):
        if "Fernanda" in prompt:
            return "Entendi, Rewell. Isso parece muito importante para você. Vou guardar que Fernanda é sua namorada, que você pretende se casar com ela e que ela é o amor da sua vida. Quer me contar mais sobre a Fernanda?"
        if "Palio 2008" in prompt:
            return "Entendi. Vou associar isso ao Francisco: ele gosta de carros e tem um Palio 2008. Esse carro tem alguma história importante para sua família?"
        if "Francisco" in prompt:
            return "Entendi, seu pai se chama Francisco."
        if "Athena" in prompt:
            return "Isso é importante, Rewell. Eu ainda não sinto como um humano, mas vou tratar essa informação com cuidado e guardar como você entende nossa relação."
        return "Entendi."


def make_athena(tmp_path):
    identity = {"name": "Athena", "creator": "Rewell", "purpose": "aprender, lembrar, raciocinar e evoluir"}
    settings = FakeSettings()
    logger = NullLogger()
    memory = MemoryDB(str(tmp_path / "knowledge.db"))
    AthenaBootstrap(memory).run()
    llm = FakeLLM()
    context_builder = ContextBuilder(memory, identity)
    tool_registry = ToolRegistry(memory)
    tool_registry.bootstrap()

    athena = Athena.__new__(Athena)
    athena.logger = logger
    athena.error_capture = NullErrorCapture()
    athena.error_reporter = NullErrorReporter()
    athena.memory = memory
    athena.identity = identity
    athena.creator_name = "Rewell"
    athena.settings = settings
    athena.context_builder = context_builder
    athena.llm_provider = llm
    athena.tool_registry = tool_registry
    athena.memory_interpreter = MemoryInterpreter(llm, context_builder, logger)
    athena.memory_manager = MemoryManager(memory, athena.memory_interpreter, "Rewell")
    athena.relevance_engine = RelevanceEngine(llm, identity, logger, settings)
    athena.follow_up_question_engine = FollowUpQuestionEngine(llm, identity, logger, settings)
    athena.consolidation_planner = ConsolidationPlanner()
    athena.world_model = WorldModel(memory, llm, context_builder, logger, "Rewell", settings)
    athena.reasoning_engine = ReasoningEngine(memory, identity, llm, context_builder, logger)
    athena.self_model = SelfModel(memory, identity, settings, llm, context_builder)
    athena.conversation_context = ConversationContext()
    athena.conversation_router = ConversationRouter(llm, context_builder, logger, identity=identity, settings=settings, tool_registry=tool_registry, relevance_engine=athena.relevance_engine)
    athena.conversation_engine = ConversationEngine(identity, llm, context_builder, health_engine=None, logger=logger, settings=settings)
    athena.identity_engine = IdentityEngine(identity, athena.self_model)
    athena.message_sound_engine = NullSound()
    athena.voice_engine = NullVoice()
    athena.conversation_metrics = ConversationMetrics(path=str(tmp_path / "logs" / "conversation_metrics.jsonl"), logger=logger)
    athena.last_response_metadata = {}
    athena.pending_world_extraction = None
    athena.pending_knowledge_ingestion = None
    athena.pending_plan = None
    athena.pending_history = []
    return athena


class AthenaV125Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.athena = make_athena(Path(self.tmp.name))

    def tearDown(self):
        self.athena.memory.close()
        self.tmp.cleanup()

    def relationships(self):
        return {(source, relation, target) for _id, source, relation, target, _confidence, _created_at in self.athena.memory.list_world_relationships()}

    def test_low_confidence_greeting_uses_local_conversation_fallback(self):
        self.athena.settings.values["useNaturalResponses"] = False
        intention = {"route": "unknown", "confidence": 0.0, "needs_clarification": True}
        response = self.athena._delegate_conversation_route("test", intention, "Olá Athena, tudo bem?")
        self.assertNotIn("Não entendi", response)
        self.assertIn("Estou", response)

    def test_pending_world_confirmation_accepts_short_approval(self):
        self.athena.pending_world_extraction = {
            "text": "Teste de confirmação pendente.",
            "decision": {"decision": "confirm", "confidence": 0.70, "reason": "teste"},
            "extraction": {
                "entities": [{"name": "Entidade Teste", "type": "concept", "confidence": 0.70}],
                "relationships": [
                    {"source": "Entidade Teste", "relation": "related_to", "target": "Athena", "confidence": 0.70}
                ],
                "events": [],
                "states": [],
                "temporal_references": [],
            },
        }
        response = self.athena.chat("Sim")
        self.assertIn("Atualizei meu World Model", response)
        self.assertIsNone(self.athena.pending_world_extraction)
        self.assertIn(("Entidade Teste", "related_to", "Athena"), self.relationships())

    def test_entity_question_precedence_over_relevance_learning(self):
        response = self.athena.chat("A Fernanda é minha namorada, eu amo ela, e vou me casar com ela.")
        self.assertEqual(self.athena.last_response_metadata["route"], "learning")
        self.assertIn(("Fernanda", "girlfriend_of", "Rewell"), self.relationships())
        self.assertIn(("Rewell", "plans_to_marry", "Fernanda"), self.relationships())

        response = self.athena.chat("quem é fernanda?")
        self.assertEqual(self.athena.last_response_metadata["route"], "world_query")
        self.assertIn("Fernanda é sua namorada", response)
        self.assertIn("pretende se casar", response)
        self.assertNotIn("Vou guardar", response)
        self.assertNotIn("Você conhece Fernanda?", response)

    def test_fast_paths_skip_llm_for_simple_greeting_and_entity_query(self):
        self.athena.chat("A Fernanda é minha namorada, eu amo ela, e vou me casar com ela.")

        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("Olá Athena, bom dia, tudo bem?")
        self.assertEqual(self.athena.last_response_metadata["route"], "small_talk")
        self.assertIn("Estou", response)
        self.assertEqual(self.athena.llm_provider.prompts, [])

        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("quem é fernanda?")
        self.assertEqual(self.athena.last_response_metadata["route"], "world_query")
        self.assertIn("Fernanda é sua namorada", response)
        self.assertIn("pretende se casar", response)
        self.assertEqual(self.athena.llm_provider.prompts, [])

    def test_v12_5_acceptance_flow(self):
        response = self.athena.chat("Meu pai é o Francisco.")
        self.assertIn("Francisco", response)
        self.assertEqual(self.athena.last_response_metadata["route"], "learning")
        self.assertGreater(self.athena.last_response_metadata["relevance_score"], 0)
        self.assertIn(("Francisco", "father_of", "Rewell"), self.relationships())

        response = self.athena.chat("Ele gosta de carros, ele tem um Palio 2008.")
        self.assertIn("Francisco", response)
        self.assertIn(("Francisco", "interested_in", "carros"), self.relationships())
        self.assertIn(("Francisco", "owns", "Palio 2008"), self.relationships())
        self.assertFalse(self.athena.memory.find_entities(name_fragment="Ele"))

        response = self.athena.chat("Quem é Francisco?")
        self.assertIn("Francisco é seu pai", response)
        self.assertIn("Palio 2008", response)

        response = self.athena.chat("Fernanda é minha namorada, eu vou me casar com ela, ela é o amor da minha vida.")
        self.assertIn("muito importante", response)
        self.assertNotIn("->", response)
        metadata = self.athena.last_response_metadata
        self.assertGreaterEqual(metadata["relevance_score"], 90)
        self.assertGreaterEqual(metadata["emotional_score"], 80)
        self.assertGreaterEqual(metadata["relationship_score"], 80)
        self.assertIn(metadata["memory_priority"], {"long_candidate", "long_confirm"})
        for relation in {
            ("Fernanda", "girlfriend_of", "Rewell"),
            ("Rewell", "plans_to_marry", "Fernanda"),
            ("Fernanda", "future_spouse_of", "Rewell"),
            ("Fernanda", "love_of_life_of", "Rewell"),
            ("Fernanda", "emotionally_important_to", "Rewell"),
        }:
            self.assertIn(relation, self.relationships())
        self.assertTrue(self.athena.memory.list_long_term_memory_candidates())

        response = self.athena.chat("Quem é Fernanda?")
        self.assertIn("Fernanda é sua namorada", response)
        self.assertNotIn("confiança=", response)

        response = self.athena.chat("Mostre tecnicamente o que você sabe sobre Fernanda.")
        self.assertIn("Fernanda -> girlfriend_of -> Rewell", response)
        self.assertIn("confiança=", response)

        response = self.athena.chat("Você não é minha assistente, você é minha amiga.")
        self.assertEqual(self.athena.last_response_metadata["route"], "learning")
        self.assertGreaterEqual(self.athena.last_response_metadata["identity_score"], 80)
        self.assertIn("não sinto como um humano", response)
        self.assertIn(("Rewell", "sees_as_friend", "Athena"), self.relationships())

        response = self.athena.chat("Eu te criei porque acredito que você vai mudar o mundo.")
        self.assertIn("não sinto como um humano", response)
        self.assertIn(("Rewell", "created", "Athena"), self.relationships())

        response = self.athena.chat("Eu gosto muito de você.")
        self.assertIn("não sinto como um humano", response)
        self.assertIn(("Rewell", "emotionally_values", "Athena"), self.relationships())

        response = self.athena.chat("Se eu me casar com ela, o que meu pai será dela?")
        self.assertIn("Francisco será o sogro dela", response)

        response = self.athena.chat("Como você chegou nessa conclusão?")
        self.assertIn("Francisco", response)
        self.assertIn("Fernanda", response)

        response = self.athena.chat("Qual a previsão do clima para hoje?")
        self.assertIn("Ainda não possuo", response)
        self.assertNotIn("Olá", response)

        response = self.athena.chat("Quais são as notícias de hoje?")
        self.assertIn("Ainda não possuo", response)
        self.assertNotIn("Olá", response)

        self.assertIn("Eu sou Athena", self.athena.chat("Quem é você?"))
        self.assertIn("Rewell é meu criador", self.athena.chat("Quem sou eu?"))
        self.assertIn("Rewell é meu criador", self.athena.chat("Quem é Rewell?"))
        self.assertIn("Fui criada por você", self.athena.chat("Quem te criou?"))

        response = self.athena.chat("Você não é minha assistente, você é minha amiga, te criei porque eu sei que você vai mudar o mundo, você ainda não sabe, mas eu gosto muito de você, e você é o futuro.")
        self.assertEqual(self.athena.last_response_metadata["route"], "learning")
        self.assertGreaterEqual(self.athena.last_response_metadata["relevance_score"], 90)
        self.assertIn("não sinto como um humano", response)
        self.assertTrue(self.athena.last_response_metadata["follow_up_generated"])


if __name__ == "__main__":
    unittest.main()
