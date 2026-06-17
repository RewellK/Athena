import unittest

from research.research_learning_engine import ResearchLearningEngine
from research.research_strategy_memory import ResearchStrategyMemory
from sources.source_discovery_engine import SourceDiscoveryEngine


class ResearchLearningEngineTests(unittest.TestCase):
    def test_missing_source_creates_needs_source_strategy(self):
        engine = ResearchLearningEngine(memory=ResearchStrategyMemory())
        proposal = SourceDiscoveryEngine().discover("Quanto custa um Civic 2020?", domain="vehicles")

        strategy = engine.observe_missing_source("vehicles", proposal.to_dict())

        self.assertEqual(strategy["domain"], "vehicles")
        self.assertEqual(strategy["status"], "needs_source")
        self.assertIn("iCarros", strategy["candidate_sources"])
        self.assertTrue(strategy["evidence_required"])
        self.assertTrue(strategy["requires_human_review"])

    def test_successful_research_creates_active_strategy(self):
        engine = ResearchLearningEngine(memory=ResearchStrategyMemory())

        strategy = engine.observe_external_result(
            "weather",
            source={
                "source_id": "weather.open_meteo",
                "freshness_ttl_seconds": 3600,
            },
            result={"evidence": {"evidence_id": "abc"}},
            status="completed",
        )

        self.assertEqual(strategy["domain"], "weather")
        self.assertEqual(strategy["preferred_source"], "weather.open_meteo")
        self.assertEqual(strategy["status"], "active")
        self.assertFalse(strategy["requires_human_review"])
        self.assertEqual(engine.active_strategy_for("weather")["preferred_source"], "weather.open_meteo")

    def test_llm_strategy_is_candidate_not_confirmed(self):
        engine = ResearchLearningEngine(memory=ResearchStrategyMemory())

        strategy = engine.learn_from_llm_suggestion(
            "news",
            "Buscar fonte validada com TTL curto e evitar opinião sem evidência.",
            candidate_sources=["GDELT"],
        )

        self.assertEqual(strategy["status"], "candidate")
        self.assertEqual(strategy["learned_from"], "llm_strategy_suggestion")
        self.assertTrue(strategy["requires_human_review"])
        self.assertIsNone(engine.active_strategy_for("news"))


if __name__ == "__main__":
    unittest.main()
