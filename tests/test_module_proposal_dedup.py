import tempfile
import unittest
from pathlib import Path

from capabilities.module_proposal_engine import ModuleProposalEngine, ModuleProposalStore
from capabilities.self_expansion_planner import SelfExpansionPlanner
from tests.test_v12_5 import make_athena


class ModuleProposalDedupTests(unittest.TestCase):
    def test_duplicate_module_proposals_increment_occurrence_count(self):
        engine = ModuleProposalEngine(store=ModuleProposalStore())
        gap = {"domain": "vehicles", "gap_type": "missing_source", "reason": "sem fonte"}

        first = engine.register(engine.propose_for_gap(gap))
        second = engine.register(engine.propose_for_gap(gap))
        proposals = engine.list_proposals()

        self.assertEqual(first["proposal_id"], second["proposal_id"])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["occurrence_count"], 2)

    def test_self_expansion_planner_creates_generic_learning_review_proposal(self):
        engine = ModuleProposalEngine(store=ModuleProposalStore())
        planner = SelfExpansionPlanner(proposal_engine=engine)

        response = planner.respond(
            "create_module_proposal",
            user_input="crie uma proposta de melhoria para painel visual de aprendizado",
        )
        proposals = engine.list_proposals()

        self.assertIn("LearningReviewPanel", response)
        self.assertEqual(proposals[0]["title"], "LearningReviewPanel")
        self.assertEqual(proposals[0]["status"], "pending_human_review")

    def test_athena_creates_geocoding_connector_from_direct_connector_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                response = athena.chat("Ok, pode criar o GeocodingConnector, se necessário.")
                metadata = athena.last_response_metadata

                self.assertEqual(metadata["route"], "memory_query")
                self.assertEqual(metadata["intent"], "create_module_proposal")
                self.assertIn("GeocodingConnector", response)
                proposals = athena.source_manager.list_module_proposals()
                self.assertEqual(proposals[0]["title"], "GeocodingConnector")
                self.assertEqual(proposals[0]["status"], "pending_human_review")
                self.assertEqual(metadata["llm_calls"], 0)
            finally:
                athena.memory.close()

    def test_athena_reuses_vehicle_module_proposal_after_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                athena.chat("Quanto custa um Civic 2020?")
                athena.chat("Sim")
                athena.chat("Quanto custa um Corolla 2021?")
                athena.chat("Sim")

                proposals = athena.source_manager.list_module_proposals(domain="vehicles")
                self.assertEqual(len(proposals), 1)
                self.assertEqual(proposals[0]["title"], "VehiclePriceConnector")
                self.assertGreaterEqual(proposals[0]["occurrence_count"], 2)
            finally:
                athena.memory.close()


if __name__ == "__main__":
    unittest.main()
