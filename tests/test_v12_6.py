import tempfile
import unittest
from pathlib import Path

from bootstrap import AthenaBootstrap
from memory.database import MemoryDB
from scripts.reset_knowledge_db import CONFIRMATION_TEXT, reset_knowledge_db
from tests.test_v12_5 import make_athena


class AthenaV126Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.athena = make_athena(Path(self.tmp.name))

    def tearDown(self):
        self.athena.memory.close()
        self.tmp.cleanup()

    def test_local_routes_expose_zero_llm_stage_metrics(self):
        cases = [
            ("bom dia, tudo bem com você?", "small_talk"),
            ("Quem é você?", "identity"),
            ("oq você pode fazer?", "capability"),
            ("Qual a previsão do clima para hoje?", "external_information"),
        ]
        metric_keys = {
            "llm_calls",
            "intent_llm_calls",
            "relevance_llm_calls",
            "extraction_llm_calls",
            "reasoning_llm_calls",
            "natural_response_llm_calls",
            "response_llm_calls",
            "follow_up_llm_calls",
        }
        for message, route in cases:
            with self.subTest(message=message):
                self.athena.llm_provider.reset_calls()
                self.athena.chat(message)
                metadata = self.athena.last_response_metadata
                self.assertEqual(metadata["route"], route)
                for key in metric_keys:
                    self.assertIn(key, metadata)
                self.assertEqual(metadata[key], 0)
            self.assertEqual(metadata["duration_ms"], metadata["total_duration_ms"])
            self.assertEqual(metadata["duration_ms"], metadata["total_ms"])
            self.assertIn("tts_duration_ms", metadata)

    def test_learned_entity_query_avoids_heavy_pipeline(self):
        self.athena.chat("A Fernanda é minha namorada, eu amo ela, e vou me casar com ela.")

        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("Quem é Fernanda?")
        metadata = self.athena.last_response_metadata

        self.assertEqual(metadata["route"], "world_query")
        self.assertIn("Fernanda é sua namorada", response)
        self.assertEqual(metadata["llm_calls"], 0)
        self.assertEqual(metadata["relevance_llm_calls"], 0)
        self.assertEqual(metadata["extraction_llm_calls"], 0)
        self.assertEqual(metadata["natural_response_llm_calls"], 0)

    def test_llm_unavailable_entity_query_uses_cognitive_control(self):
        self.athena.settings.values["useLLM"] = False
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("que legal, consegue me falar quem é a Fernanda?")
        metadata = self.athena.last_response_metadata

        self.assertEqual(metadata["route"], "world_query")
        self.assertEqual(metadata["intent"], "entity_query")
        self.assertEqual(metadata["target"], "Fernanda")
        self.assertIn("Ainda não tenho informações suficientes", response)
        self.assertNotIn("Não entendi", response)
        self.assertEqual(metadata["llm_calls"], 0)

    def test_llm_unavailable_learning_candidate_does_not_fall_to_unknown(self):
        self.athena.settings.values["useLLM"] = False
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("Fernanda é minha namorada.")
        metadata = self.athena.last_response_metadata

        self.assertEqual(metadata["route"], "learning")
        self.assertEqual(metadata["intent"], "learning_candidate")
        self.assertEqual(metadata["target"], "Fernanda")
        self.assertIn("ensinando algo novo", response)
        self.assertNotIn("Não entendi", response)
        self.assertEqual(metadata["llm_calls"], 0)

    def test_llm_unavailable_teach_intent_is_local(self):
        self.athena.settings.values["useLLM"] = False
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("Entendi, posso te ensinar, que tal?")
        metadata = self.athena.last_response_metadata

        self.assertEqual(metadata["route"], "teach_intent")
        self.assertEqual(metadata["intent"], "teach_intent")
        self.assertIn("Pode me ensinar", response)
        self.assertEqual(metadata["llm_calls"], 0)

    def test_messy_entity_query_pronoun_and_typo_use_recent_context(self):
        response = self.athena.chat("Perfeito, você sabe que é a fernanda?")
        metadata = self.athena.last_response_metadata
        self.assertEqual(metadata["route"], "world_query")
        self.assertEqual(metadata["target"], "Fernanda")
        self.assertIn("Ainda não tenho informações suficientes", response)
        self.assertNotIn("não sinto", response.lower())
        self.assertEqual(metadata["llm_calls"], 0)

        response = self.athena.chat("quero saber oq você sabe sobre ela.")
        metadata = self.athena.last_response_metadata
        self.assertEqual(metadata["route"], "world_query")
        self.assertEqual(metadata["target"], "Fernanda")
        self.assertIn("Fernanda", response)
        self.assertEqual(metadata["llm_calls"], 0)

        response = self.athena.chat("quero que me fale sobre a Fernadna")
        metadata = self.athena.last_response_metadata
        self.assertEqual(metadata["route"], "world_query")
        self.assertEqual(metadata["target"], "Fernanda")
        self.assertIn("Fernanda", response)
        self.assertEqual(metadata["llm_calls"], 0)

    def test_pronoun_recall_after_learning_known_entity_is_local(self):
        self.athena.chat("Fernanda é minha namorada.")
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("quem é ela?")
        metadata = self.athena.last_response_metadata

        self.assertEqual(metadata["route"], "world_query")
        self.assertEqual(metadata["target"], "Fernanda")
        self.assertIn("Fernanda é sua namorada", response)
        self.assertEqual(metadata["llm_calls"], 0)

        response = self.athena.chat("me fala dela")
        metadata = self.athena.last_response_metadata
        self.assertEqual(metadata["target"], "Fernanda")
        self.assertIn("Fernanda é sua namorada", response)
        self.assertEqual(metadata["llm_calls"], 0)

    def test_user_relation_and_entity_pronoun_context(self):
        self.athena.chat("Meu pai é Francisco.")

        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("quem é meu pai?")
        self.assertEqual(self.athena.last_response_metadata["route"], "world_query")
        self.assertIn("Francisco é seu pai", response)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

        response = self.athena.chat("ele gosta de carro.")
        self.assertEqual(self.athena.last_response_metadata["route"], "learning")
        self.assertEqual(self.athena.last_response_metadata["target"], "Francisco")
        self.assertIn("Francisco", response)

        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("o que você sabe sobre ele?")
        self.assertEqual(self.athena.last_response_metadata["target"], "Francisco")
        self.assertIn("Francisco é seu pai", response)
        self.assertIn("gosta de carro", response)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_limitations_and_acknowledgement_are_local(self):
        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("e oq você ainda não consegue?")
        self.assertEqual(self.athena.last_response_metadata["route"], "capability")
        self.assertIn("ainda não consigo", response)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

        self.athena.llm_provider.reset_calls()
        response = self.athena.chat("sim")
        self.assertEqual(self.athena.last_response_metadata["route"], "conversation")
        self.assertIn("Certo", response)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_self_relationship_query_uses_learned_relationship(self):
        self.athena.chat("Você não é minha assistente, você é minha amiga.")
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("quem é você pra mim?")
        metadata = self.athena.last_response_metadata

        self.assertEqual(metadata["route"], "identity")
        self.assertIn("amiga", response)
        self.assertIn("não sinto como um humano", response)
        self.assertEqual(metadata["llm_calls"], 0)

    def test_pending_confirmation_and_identity_are_non_blocking(self):
        self.athena.pending_world_extraction = self.athena._make_pending(
            "world_model_confirmation",
            "Pessoa Exemplo é importante.",
            extraction={
                "entities": [{"name": "Pessoa Exemplo", "type": "person", "confidence": 0.70}],
                "relationships": [],
                "events": [],
                "states": [],
                "temporal_references": [],
            },
            decision={"decision": "confirm", "confidence": 0.70, "reason": "teste"},
        )

        response = self.athena.chat("ótimo, quem é você?")
        self.assertEqual(self.athena.last_response_metadata["route"], "identity")
        self.assertIn("Eu sou Athena", response)
        self.assertIsNotNone(self.athena.pending_world_extraction)

        response = self.athena.chat("sim")
        self.assertEqual(self.athena.last_response_metadata["route"], "pending_confirmation")
        self.assertIn("Atualizei meu World Model", response)
        self.assertIsNone(self.athena.pending_world_extraction)

    def test_unknown_recovery_without_recent_failure_does_not_loop(self):
        response = self.athena.chat("o que você não entendeu?")
        self.assertEqual(self.athena.last_response_metadata["route"], "system")
        self.assertEqual(self.athena.last_response_metadata["intent"], "unknown_recovery")
        self.assertIn("Não tenho uma falha de classificação recente", response)
        self.assertNotEqual(response, "Não entendi com segurança o que você quer agora. Pode me explicar de outro jeito?")

    def test_current_external_requests_do_not_invent_without_tool(self):
        for message in [
            "Qual o preço atual do bitcoin?",
            "Quais eventos atuais estão acontecendo?",
        ]:
            with self.subTest(message=message):
                self.athena.llm_provider.reset_calls()
                response = self.athena.chat(message)
                self.assertEqual(self.athena.last_response_metadata["route"], "external_information")
                self.assertIn("Ainda não possuo", response)
                self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_asl_flag_is_disabled_by_default(self):
        self.assertFalse(self.athena.settings.get("useAthenaSemanticLanguage", True))

    def test_safe_reset_requires_confirmation_and_recreates_db_with_backup(self):
        root = Path(self.tmp.name) / "reset_case"
        root.mkdir()
        db_path = root / "knowledge.db"
        backup_root = root / "backups"

        memory = MemoryDB(str(db_path))
        try:
            AthenaBootstrap(memory).run()
            bootstrap_entities = memory.count_entities()
            memory.save_entity("Entidade Temporária", "concept")
            self.assertEqual(memory.count_entities(), bootstrap_entities + 1)
        finally:
            memory.close()

        with self.assertRaises(ValueError):
            reset_knowledge_db(db_path=db_path, backup_root=backup_root, confirm="")

        result = reset_knowledge_db(db_path=db_path, backup_root=backup_root, confirm=CONFIRMATION_TEXT)
        self.assertTrue(result["recreated"])
        self.assertTrue(Path(result["backup_dir"]).exists())
        self.assertTrue((Path(result["backup_dir"]) / "knowledge.db").exists())

        recreated = MemoryDB(str(db_path))
        try:
            self.assertEqual(recreated.count_entities(), bootstrap_entities)
            self.assertFalse(recreated.find_entities(name_fragment="Entidade Temporária"))
        finally:
            recreated.close()


if __name__ == "__main__":
    unittest.main()
