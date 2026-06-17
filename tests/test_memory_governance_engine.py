import tempfile
import unittest
from pathlib import Path

from memory.database import MemoryDB
from memory_governance.memory_admin_engine import MemoryAdminEngine
from memory_governance.memory_governance_engine import MemoryGovernanceEngine
from learning.self_insight_engine import SelfInsightEngine, SelfInsightStore


class MemoryGovernanceEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = MemoryDB(str(Path(self.tmp.name) / "knowledge.db"))

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def test_lists_pending_and_important_memories_without_deleting(self):
        self.memory.save_short_term_memory("Candidato de memória para revisar", importance_score=42)
        self.memory.save_memory_relevance(
            "short_term",
            1,
            "Memória emocional importante",
            {
                "relevance_score": 90,
                "emotional_score": 80,
                "memory_priority": "long_confirm",
                "confirmation_required": True,
                "related_entities": ["Fernanda"],
            },
            source_message="Mensagem origem",
        )

        governance = MemoryGovernanceEngine(self.memory)

        pending = governance.pending_memories()
        important = governance.important_memories()
        snapshot = governance.snapshot()

        self.assertTrue(pending)
        self.assertTrue(important)
        self.assertGreaterEqual(snapshot["counts"]["short_term_candidate"], 1)
        self.assertEqual(self.memory.count_short_term_memory(), 1)

    def test_memory_admin_reports_self_insights_as_improvements(self):
        insight_engine = SelfInsightEngine(store=SelfInsightStore())
        insight_engine.create_learning_to_learn_insight(
            source="test",
            content="Preciso transformar falhas em exemplos de treino.",
            suggested_action="Criar TrainingExample a partir de ReflectionEvent.",
            suggested_test="ReflectionEvent deve gerar TrainingExample candidate.",
        )
        admin = MemoryAdminEngine(
            memory=self.memory,
            governance_engine=MemoryGovernanceEngine(self.memory),
            self_insight_engine=insight_engine,
        )

        response = admin.respond({"operation": "improvement_memories"})

        self.assertIn("insights pendentes", response)
        self.assertIn("Reflection", response)


if __name__ == "__main__":
    unittest.main()
