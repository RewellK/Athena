import tempfile
import unittest
from pathlib import Path

from learning.async_llm_teacher_loop import AsyncLlmTeacherLoop, LlmTeacherInsightStore
from tests.test_linguistic_learning_platform import Settings, TeacherLLM
from tests.test_v12_5 import make_athena


class AsyncLlmTeacherSafetyTests(unittest.TestCase):
    def test_disabled_teacher_loop_is_not_enqueued_by_athena_chat(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                athena.settings.values["asyncLlmTeacherEnabled"] = False
                response = athena.chat("Oi")

                self.assertIn("Olá", response)
                self.assertNotIn("llm_teacher_pending", athena.last_response_metadata)
                self.assertEqual(athena.async_llm_teacher_loop.pending_count(), 0)
            finally:
                athena.memory.close()

    def test_teacher_failure_returns_candidate_without_raising(self):
        teacher = AsyncLlmTeacherLoop(
            llm_provider=TeacherLLM(error=RuntimeError("offline")),
            store=LlmTeacherInsightStore(),
            settings=Settings({"asyncLlmTeacherEnabled": True}),
        )

        teacher.enqueue_turn("pergunta", "resposta", metadata={"route": "unknown"})
        insight = teacher.process_pending_once()

        self.assertEqual(insight["status"], "candidate")
        self.assertTrue(insight["requires_human_review"])
        self.assertIn("falhou sem quebrar", insight["summary"])


if __name__ == "__main__":
    unittest.main()
