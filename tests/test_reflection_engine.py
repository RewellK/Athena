import tempfile
import unittest
from pathlib import Path

from reflection.reflection_engine import ReflectionEngine
from reflection.reflection_store import ReflectionStore


class FakeSettings:
    def __init__(self, values=None):
        self.values = {
            "reflectionEnabled": True,
            "reflectionUseLlmResponse": False,
            "reflectionSlowRecallMs": 2500,
        }
        self.values.update(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)


class ExplodingLLM:
    def __init__(self):
        self.calls = 0

    def generate(self, *_args, **_kwargs):
        self.calls += 1
        raise AssertionError("ReflectionEngine should not call LLM by default")


class ReflectionEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store_path = Path(self.tmp.name) / "reflection_events.jsonl"
        self.llm = ExplodingLLM()
        self.engine = ReflectionEngine(
            memory=None,
            identity={"name": "Athena", "creator": "Rewell"},
            llm_provider=self.llm,
            store=ReflectionStore(path=str(self.store_path)),
            settings=FakeSettings(),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def issue_types(self, events):
        return {event.issue_type for event in events}

    def test_wrong_target_self_feeling_generates_human_review_event(self):
        events = self.engine.observe_turn(
            "quem é Fernanda?",
            "Eu ainda não sinto como um humano, mas vou tratar essa informação com cuidado.",
            metadata={
                "route": "world_query",
                "intent": "entity_query",
                "target": "Fernanda",
                "llm_calls": 0,
                "used_world_model": True,
            },
        )

        self.assertEqual(self.issue_types(events), {"wrong_target"})
        event = events[0]
        self.assertEqual(event.severity, "high")
        self.assertTrue(event.requires_human_review)
        self.assertFalse(event.accepted)
        self.assertIn("self-feeling", event.suggestion)
        self.assertTrue(event.suggested_tests)
        self.assertEqual(self.engine.store.count(), 1)

    def test_unknown_pronoun_failure_and_recent_entity_failure_are_detected(self):
        events = self.engine.analyze_turn(
            "quero saber o que você sabe sobre ela",
            "Não entendi com segurança o que você quer agora. Pode me explicar de outro jeito?",
            metadata={
                "route": "unknown",
                "intent": "unknown",
                "target": "",
                "recent_entities": ["Fernanda"],
                "needs_clarification": True,
            },
        )

        self.assertIn("unknown_loop", self.issue_types(events))
        self.assertIn("missing_pronoun_resolution", self.issue_types(events))
        self.assertIn("recent_entity_resolution_failed", self.issue_types(events))
        for event in events:
            self.assertTrue(event.suggested_tests)

    def test_simple_route_llm_overuse_is_detected_without_llm_critic(self):
        events = self.engine.observe_turn(
            "oq você pode fazer?",
            "Eu posso conversar, lembrar e consultar meu World Model.",
            metadata={
                "route": "capability",
                "intent": "capability_query",
                "target": "Athena",
                "llm_calls": 2,
            },
        )

        self.assertIn("llm_overuse", self.issue_types(events))
        self.assertEqual(self.llm.calls, 0)

    def test_tool_hallucination_pending_block_and_slow_recall_are_detected(self):
        tool_events = self.engine.analyze_turn(
            "qual a previsão do clima amanhã?",
            "Amanhã vai chover em São Paulo.",
            metadata={
                "route": "external_information",
                "intent": "weather_query",
                "tool_available": False,
                "used_tool": False,
                "llm_calls": 0,
            },
        )
        self.assertIn("tool_hallucination", self.issue_types(tool_events))

        pending_events = self.engine.analyze_turn(
            "quem é você?",
            "Ainda preciso saber se você autoriza salvar a estrutura proposta.",
            metadata={
                "route": "pending_confirmation",
                "intent": "pending_confirmation",
                "pending_confirmation": "world_model_confirmation",
                "llm_calls": 0,
            },
        )
        self.assertIn("pending_confirmation_blocking_topic_switch", self.issue_types(pending_events))

        slow_events = self.engine.analyze_turn(
            "quem é Fernanda?",
            "Fernanda é sua namorada.",
            metadata={
                "route": "world_query",
                "intent": "entity_query",
                "target": "Fernanda",
                "used_memory": True,
                "used_world_model": True,
                "duration_ms": 3000,
                "llm_calls": 0,
            },
        )
        self.assertIn("slow_known_recall", self.issue_types(slow_events))

    def test_local_report_uses_stored_hypotheses_and_does_not_call_llm(self):
        self.engine.observe_turn(
            "quem é Fernanda?",
            "Eu ainda não sinto como um humano.",
            metadata={"route": "world_query", "intent": "entity_query", "target": "Fernanda"},
        )

        response = self.engine.respond("o que você acha que precisa melhorar?")

        self.assertIn("hipótese de falha", response)
        self.assertIn("wrong_target", response)
        self.assertIn("revisão humana", response)
        self.assertEqual(self.llm.calls, 0)


if __name__ == "__main__":
    unittest.main()
