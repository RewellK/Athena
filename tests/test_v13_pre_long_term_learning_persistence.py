import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from tests.test_v12_5 import make_athena


class AthenaV13PreLongTermLearningPersistenceTests(unittest.TestCase):
    def test_approved_learning_survives_restart_and_multiday_gap_without_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            athena = make_athena(root)
            try:
                athena.chat("Athena, iniciar runtime.")
                athena.chat("Athena, comando aprendizagem.")
                athena.chat("Conversas diárias devem ir para buffer temporário antes de virar memória permanente.")
                athena.chat("Relatórios descartáveis não devem virar memória confirmada.")
                athena.runtime_supervisor.run_once()

                report = athena.chat("Athena, relatório aprendizagem.")
                self.assertIn("Conversas diárias", report)
                self.assertIn("Relatórios descartáveis", report)
                self.assertEqual(athena.memory.count_real_long_term_memory(), 0)

                athena.chat("Aprovar candidato 1.")
                athena.chat("Rejeitar candidato 2.")
                consolidated = athena.chat("Consolidar aprovados.")
                self.assertIn("Consolidei 1", consolidated)

                rows = athena.memory.list_long_term_memory_with_metadata()
                self.assertEqual(len(rows), 1)
                _id, content, source, _importance, _created_at, metadata = rows[0]
                self.assertIn("Conversas diárias", content)
                self.assertEqual(source, "supervised_learning_session")
                self.assertEqual(metadata["approved_by"], "user")
                self.assertEqual(metadata["status"], "confirmed/promoted")
                self.assertEqual(metadata["source"], "local_heuristic")
                self.assertTrue(metadata["original_candidate_id"])
                self.assertIn(metadata["candidate_type"], {"memory_policy", "project_principle", "architecture_rule"})

                shutdown = athena.chat("Athena, desligar runtime.")
                self.assertIn("Runtime encerrado com segurança", shutdown)
            finally:
                athena.memory.close()

            reopened = make_athena(root)
            try:
                reopened.llm_provider.reset_calls()
                answer = reopened.chat("O que você aprendeu sobre conversas diárias?")
                self.assertIn("aprendi localmente", answer)
                self.assertIn("buffer temporário", answer)
                self.assertIn("Origem: supervised_learning_session", answer)
                self.assertEqual(reopened.last_response_metadata["llm_calls"], 0)

                rejected_answer = reopened.chat("O que você aprendeu sobre relatórios descartáveis?")
                self.assertNotIn("aprendi localmente", rejected_answer)
                self.assertNotIn("Relatórios descartáveis não devem virar memória confirmada", rejected_answer)

                reopened.day_memory_buffer.discard()
                for candidate in reopened.learning_candidate_store.list(limit=100000):
                    reopened.learning_candidate_store.update_status(candidate.get("id"), "discarded")

                past = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
                rows = reopened.memory.list_long_term_memory_with_metadata()
                memory_id = rows[0][0]
                metadata = dict(rows[0][5])
                metadata["created_at"] = past
                metadata["promoted_at"] = past
                reopened.memory.conn.execute(
                    "UPDATE long_term_memory SET created_at = ?, metadata_json = ? WHERE id = ?",
                    (past, json.dumps(metadata, ensure_ascii=False, sort_keys=True), memory_id),
                )
                reopened.memory.conn.commit()

                reopened.llm_provider.reset_calls()
                multiday_answer = reopened.chat("O que você sabe sobre memória diária?")
                self.assertIn("aprendi localmente", multiday_answer)
                self.assertIn("buffer temporário", multiday_answer)
                self.assertEqual(reopened.last_response_metadata["llm_calls"], 0)
            finally:
                reopened.memory.close()


if __name__ == "__main__":
    unittest.main()
