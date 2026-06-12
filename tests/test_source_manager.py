import tempfile
import time
import unittest
from pathlib import Path

from sources.source_discovery_engine import SourceDiscoveryEngine
from sources.source_manager import SourceManager
from sources.source_registry import SourceRegistry
from tests.test_v12_5 import make_athena


class SourceManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = str(Path(self.tmp.name) / "source_registry.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_vehicle_source_generates_candidate_proposal(self):
        manager = SourceManager(registry=SourceRegistry(path=self.registry_path))

        result = manager.handle_external_request("Quanto custa um Civic 2020?")

        self.assertEqual(result["status"], "missing_source")
        self.assertEqual(result["domain"], "vehicles")
        self.assertEqual(result["proposal"]["name"], "iCarros")
        self.assertEqual(result["proposal"]["status"], "candidate")
        self.assertTrue(result["proposal"]["requires_human_approval"])
        self.assertIn("fonte candidata", result["response"])

    def test_source_candidate_is_saved_without_becoming_enabled(self):
        manager = SourceManager(registry=SourceRegistry(path=self.registry_path))
        proposal = SourceDiscoveryEngine().discover("Quanto custa um Civic 2020?", domain="vehicles")

        result = manager.add_candidate(proposal.to_dict())
        source = result["source"]

        self.assertEqual(source["status"], "pending_validation")
        self.assertFalse(source["enabled"])
        self.assertNotEqual(source["validation_status"], "passed")
        self.assertFalse(result["evidence_note"]["can_support_factual_answer"])

    def test_rejected_source_is_not_enabled(self):
        manager = SourceManager(registry=SourceRegistry(path=self.registry_path))
        proposal = SourceDiscoveryEngine().discover("notícias de hoje", domain="news")

        rejected = manager.reject_candidate(proposal.to_dict())

        self.assertEqual(rejected["status"], "rejected")
        self.assertFalse(rejected["enabled"])
        self.assertFalse(manager.registry.has_enabled_source("news"))

    def test_athena_suggests_source_and_waits_for_human_approval(self):
        athena = make_athena(Path(self.tmp.name))
        try:
            started_at = time.perf_counter()
            response = athena.chat("Athena, quanto custa um Civic 2020?")
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)

            metadata = athena.last_response_metadata
            self.assertEqual(metadata["route"], "external_information")
            self.assertEqual(metadata["external_domain"], "vehicles")
            self.assertEqual(metadata["source_status"], "missing_source")
            self.assertIn("Não sei consultar veículos ainda", response)
            self.assertIn("iCarros", response)
            self.assertIsNotNone(athena.pending_source_proposal)
            self.assertLess(elapsed_ms, 500)

            response = athena.chat("sim")
            self.assertEqual(athena.last_response_metadata["route"], "pending_confirmation")
            self.assertIn("fonte candidata", response)
            self.assertIn("desativada", response)
            self.assertIsNone(athena.pending_source_proposal)
            self.assertFalse(athena.source_manager.registry.has_enabled_source("vehicles"))
        finally:
            athena.memory.close()

    def test_athena_does_not_invent_news_without_source(self):
        athena = make_athena(Path(self.tmp.name))
        try:
            response = athena.chat("Quais são as notícias de hoje?")
            metadata = athena.last_response_metadata

            self.assertEqual(metadata["route"], "external_information")
            self.assertEqual(metadata["external_domain"], "news")
            self.assertEqual(metadata["source_status"], "missing_source")
            self.assertIn("Não sei consultar notícias ainda", response)
            self.assertNotIn("manchete:", response.lower())
            self.assertEqual(metadata["llm_calls"], 0)
        finally:
            athena.memory.close()


if __name__ == "__main__":
    unittest.main()
