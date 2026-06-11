import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from tests.test_v12_5 import FakeSettings, NullLogger, make_athena
from voice.voice_engine import VoiceEngine


class SlowVoiceProvider:
    provider_id = "slow_test"

    def __init__(self, _settings=None, _logger=None):
        pass

    def speak(self, _text):
        time.sleep(0.35)
        return True


class AthenaV1251Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.athena = make_athena(Path(self.tmp.name))

    def tearDown(self):
        self.athena.memory.close()
        self.tmp.cleanup()

    def relationships(self):
        return {
            (source, relation, target)
            for _id, source, relation, target, _confidence, _created_at
            in self.athena.memory.list_world_relationships()
        }

    def test_startup_greeting_is_local_and_does_not_touch_memory(self):
        before = (
            self.athena.memory.count_short_term_memory(),
            self.athena.memory.count_entities(),
            self.athena.memory.count_world_relationships(),
        )
        self.athena.llm_provider.reset_calls()

        response = self.athena.startup_greeting(now=datetime(2026, 6, 11, 9, 0), speak=False)

        after = (
            self.athena.memory.count_short_term_memory(),
            self.athena.memory.count_entities(),
            self.athena.memory.count_world_relationships(),
        )
        self.assertIn("Bom dia", response)
        self.assertIn("Athena iniciada", response)
        self.assertEqual(before, after)
        self.assertEqual(self.athena.llm_provider.prompts, [])
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_pending_confirmation_does_not_block_new_topic(self):
        self.athena.pending_world_extraction = self.athena._make_pending(
            "world_model_confirmation",
            "Meu pai é Francisco.",
            decision={"decision": "confirm", "confidence": 0.70, "reason": "teste"},
            extraction={
                "entities": [{"name": "Francisco", "type": "person", "confidence": 0.70}],
                "relationships": [{"source": "Francisco", "relation": "father_of", "target": "Rewell", "confidence": 0.70}],
                "events": [],
                "states": [],
                "temporal_references": [],
            },
        )
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("Ótimo, quem é você?")

        self.assertIn("Eu sou Athena", response)
        self.assertIn("Ainda deixei pendente", response)
        self.assertIsNotNone(self.athena.pending_world_extraction)
        self.assertEqual(self.athena.llm_provider.prompts, [])
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_pending_confirmation_accepts_short_approval_without_llm(self):
        self.athena.pending_world_extraction = self.athena._make_pending(
            "world_model_confirmation",
            "Meu pai é Francisco.",
            decision={"decision": "confirm", "confidence": 0.70, "reason": "teste"},
            extraction={
                "entities": [{"name": "Francisco", "type": "person", "confidence": 0.70}],
                "relationships": [{"source": "Francisco", "relation": "father_of", "target": "Rewell", "confidence": 0.70}],
                "events": [],
                "states": [],
                "temporal_references": [],
            },
        )
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("Sim")

        self.assertIn("Atualizei meu World Model", response)
        self.assertIsNone(self.athena.pending_world_extraction)
        self.assertIn(("Francisco", "father_of", "Rewell"), self.relationships())
        self.assertEqual(self.athena.llm_provider.prompts, [])
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_learned_entity_query_uses_local_world_model(self):
        self.athena.chat("A Fernanda é minha namorada, eu amo ela, e vou me casar com ela.")
        self.assertIn(("Fernanda", "girlfriend_of", "Rewell"), self.relationships())

        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("Quem é Fernanda?")

        self.assertIn("Fernanda é sua namorada", response)
        self.assertIn("pretende se casar", response)
        self.assertEqual(self.athena.last_response_metadata["route"], "world_query")
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)
        self.assertEqual(self.athena.llm_provider.prompts, [])

    def test_simple_local_routes_skip_llm(self):
        cases = [
            ("Olá Athena, bom dia, tudo bem?", "small_talk", "Estou"),
            ("Quem é você?", "identity", "Eu sou Athena"),
            ("Qual foi seu último erro?", "error_query", "Nenhum erro"),
            ("Qual a previsão do clima para hoje?", "external_information", "Ainda não possuo"),
        ]
        for message, expected_route, expected_text in cases:
            with self.subTest(message=message):
                self.athena.llm_provider.reset_calls()
                response = self.athena.chat(message)
                self.assertEqual(self.athena.last_response_metadata["route"], expected_route)
                self.assertIn(expected_text, response)
                self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)
                self.assertEqual(self.athena.llm_provider.prompts, [])

    def test_capability_queries_use_local_capability_engine(self):
        cases = [
            ("oq você pode fazer?", "Eu posso conversar"),
            ("quais são suas capacidades?", "ferramentas configuradas"),
        ]
        for message, expected_text in cases:
            with self.subTest(message=message):
                self.athena.llm_provider.reset_calls()
                response = self.athena.chat(message)
                self.assertEqual(self.athena.last_response_metadata["route"], "capability")
                self.assertEqual(self.athena.last_response_metadata["intent"], "capability_query")
                self.assertIn(expected_text, response)
                self.assertIn("clima/notícias", response)
                self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)
                self.assertEqual(self.athena.llm_provider.prompts, [])

    def test_positive_day_with_capability_question_keeps_capability_as_main_intent(self):
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("Hoje meu dia foi muito bom, oque você pode fazer?")

        self.assertEqual(self.athena.last_response_metadata["route"], "capability")
        self.assertEqual(self.athena.last_response_metadata["intent"], "capability_query")
        self.assertIn("Que bom que seu dia foi bom", response)
        self.assertIn("Eu posso conversar", response)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)
        self.assertEqual(self.athena.llm_provider.prompts, [])

    def test_unknown_recovery_explains_previous_classification_failure(self):
        self.athena.settings.values["useFastConversationPath"] = False
        self.athena.settings.values["useLLM"] = False
        first = self.athena.chat("zorb flarn sem rota clara")
        self.assertIn("Não entendi com segurança", first)
        self.assertIsNotNone(self.athena.last_unknown_interaction)

        self.athena.settings.values["useFastConversationPath"] = True
        self.athena.settings.values["useLLM"] = True
        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("oq você não entendeu?")

        self.assertEqual(self.athena.last_response_metadata["route"], "system")
        self.assertIn("falhei ao classificar", response)
        self.assertIn("zorb flarn", response)
        self.assertNotIn("Pode me explicar de outro jeito?", response)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)
        self.assertEqual(self.athena.llm_provider.prompts, [])

    def test_voice_speak_returns_before_provider_finishes(self):
        settings = FakeSettings(
            {
                "voiceEnabled": True,
                "voiceSpeakResponses": True,
                "voiceProvider": "slow_test",
                "fallbackVoiceProvider": "none",
            }
        )
        original = dict(VoiceEngine(settings, NullLogger()).manager.PROVIDERS)
        try:
            VoiceEngine(settings, NullLogger()).manager.PROVIDERS["slow_test"] = SlowVoiceProvider
            engine = VoiceEngine(settings, NullLogger())
            started_at = time.perf_counter()
            queued = engine.speak("teste")
            elapsed = time.perf_counter() - started_at
            self.assertTrue(queued)
            self.assertLess(elapsed, 0.15)
            time.sleep(0.45)
            self.assertEqual(engine.status()["last_provider"], "slow_test")
        finally:
            VoiceEngine(settings, NullLogger()).manager.PROVIDERS.clear()
            VoiceEngine(settings, NullLogger()).manager.PROVIDERS.update(original)


if __name__ == "__main__":
    unittest.main()
