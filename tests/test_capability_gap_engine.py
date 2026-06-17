import tempfile
import unittest
from pathlib import Path

from capabilities.capability_gap_engine import CapabilityGapEngine
from capabilities.module_proposal_engine import ModuleProposalEngine, ModuleProposalStore
from capabilities.self_expansion_planner import SelfExpansionPlanner
from learning.self_insight_engine import SelfInsightEngine, SelfInsightStore
from research.research_learning_engine import ResearchLearningEngine
from research.research_strategy_memory import ResearchStrategyMemory
from tests.test_v12_5 import make_athena


class CapabilityGapEngineTests(unittest.TestCase):
    def test_gap_engine_detects_missing_vehicle_source_and_module_proposal(self):
        gap_engine = CapabilityGapEngine()
        proposal_engine = ModuleProposalEngine(store=ModuleProposalStore())

        gap = gap_engine.detect_external_gap(
            "vehicles",
            "missing_source",
            query="Quanto custa um Civic 2020?",
            source_proposal={"name": "Fonte de veículos candidata"},
        )
        proposal = proposal_engine.propose_for_gap(gap, source_proposal={"name": "Fonte de veículos candidata"})

        self.assertEqual(gap["gap_type"], "missing_source")
        self.assertEqual(gap["domain"], "vehicles")
        self.assertEqual(proposal["title"], "VehiclePriceConnector")
        self.assertEqual(proposal["status"], "proposed")
        self.assertTrue(proposal["human_approval_required"])
        self.assertTrue(proposal["risks"])
        self.assertTrue(proposal["suggested_tests"])

    def test_module_proposal_can_be_registered_approved_and_rejected_without_code_execution(self):
        engine = ModuleProposalEngine(store=ModuleProposalStore())
        proposal = engine.propose_for_gap({"domain": "news", "gap_type": "missing_source", "reason": "sem fonte"})

        saved = engine.register(proposal)
        listed = engine.list_proposals()
        approved = engine.approve(saved["proposal_id"])
        rejected = engine.reject(saved["proposal_id"])

        self.assertEqual(saved["status"], "pending_human_review")
        self.assertEqual(listed[0]["title"], "NewsResearchConnector")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(rejected["status"], "rejected")
        self.assertNotIn("implemented", {saved["status"], approved["status"]})

    def test_self_insight_and_research_learning_receive_capability_gap(self):
        insight_engine = SelfInsightEngine(store=SelfInsightStore())
        research = ResearchLearningEngine(memory=ResearchStrategyMemory())
        gap = {"domain": "vehicles", "gap_type": "missing_source", "reason": "sem fonte validada"}
        proposal = ModuleProposalEngine(store=ModuleProposalStore()).propose_for_gap(gap)

        insight = insight_engine.create_from_capability_gap(gap, proposal)
        strategy = research.observe_capability_gap("vehicles", gap=gap, module_proposal=proposal)

        self.assertEqual(insight["insight_type"], "missing_capability")
        self.assertEqual(insight["status"], "pending_human_review")
        self.assertEqual(strategy["status"], "needs_source")
        self.assertTrue(strategy["requires_human_review"])

    def test_self_expansion_planner_lists_local_proposals_without_llm(self):
        engine = ModuleProposalEngine(store=ModuleProposalStore())
        saved = engine.register(engine.propose_for_gap({"domain": "vehicles", "gap_type": "missing_source", "reason": "sem fonte"}))
        planner = SelfExpansionPlanner(proposal_engine=engine)

        response = planner.respond("module_proposals")
        approve = planner.respond("approve_module_proposal", identifier=saved["proposal_id"])

        self.assertIn("VehiclePriceConnector", response)
        self.assertIn("Proposta aprovada", approve)

    def test_athena_vehicle_request_creates_source_and_module_proposal_on_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                response = athena.chat("Quanto custa um Civic 2020?")
                metadata = athena.last_response_metadata

                self.assertEqual(metadata["route"], "external_information")
                self.assertEqual(metadata["external_domain"], "vehicles")
                self.assertEqual(metadata["source_status"], "missing_source")
                self.assertEqual(metadata["capability_gap_type"], "missing_source")
                self.assertEqual(metadata["module_proposal_title"], "VehiclePriceConnector")
                self.assertIn("proposta de módulo", response)
                self.assertIn("iCarros", response)
                self.assertNotIn("R$", response)
                self.assertEqual(metadata["llm_calls"], 0)

                response = athena.chat("Sim")
                self.assertIn("fonte candidata", response)
                self.assertIn("VehiclePriceConnector", response)
                self.assertFalse(athena.source_manager.registry.has_enabled_source("vehicles"))

                proposals = athena.source_manager.list_module_proposals()
                self.assertEqual(proposals[0]["title"], "VehiclePriceConnector")
                self.assertEqual(proposals[0]["status"], "pending_human_review")

                response = athena.chat("quais módulos você acha que precisa?")
                self.assertIn("VehiclePriceConnector", response)

                response = athena.chat("tem algo que você precisa melhorar?")
                self.assertIn("missing_capability", response)
            finally:
                athena.memory.close()


if __name__ == "__main__":
    unittest.main()
