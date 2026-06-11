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
