import tempfile
import unittest
from pathlib import Path

from runtime import RuntimeStateStore, RuntimeSupervisor, WorkerScheduler
from tests.test_v12_5 import make_athena


class FailingWorker:
    def run_once(self):
        raise RuntimeError("falha simulada")


class AthenaV13PreRuntimePresenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.athena = make_athena(Path(self.tmp.name))

    def tearDown(self):
        self.athena.memory.close()
        self.tmp.cleanup()

    def test_runtime_supervisor_start_pause_resume_and_run_once(self):
        status = self.athena.runtime_supervisor.start(background=False)
        self.assertEqual(status["state"], "idle")

        paused = self.athena.runtime_supervisor.pause()
        self.assertTrue(paused["paused"])

        resumed = self.athena.runtime_supervisor.resume()
        self.assertFalse(resumed["paused"])

        result = self.athena.runtime_supervisor.run_once()
        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(result["workers_run"], 1)
        self.assertTrue(self.athena.runtime_supervisor.get_status()["last_heartbeat_at"])

    def test_runtime_shutdown_persists_state_and_restart_recovers_snapshot(self):
        state_path = str(Path(self.tmp.name) / "runtime_state.json")
        first = RuntimeSupervisor(
            state_store=RuntimeStateStore(state_path),
            settings=self.athena.settings,
        )
        first.start(background=False)
        stopped = first.stop(reason="test_shutdown")

        self.assertEqual(stopped["status"], "stopped")
        restored = RuntimeSupervisor(
            state_store=RuntimeStateStore(state_path),
            settings=self.athena.settings,
        )
        status = restored.get_status()
        self.assertEqual(status["state"], "stopped")
        self.assertTrue(status["last_shutdown_at"])

    def test_worker_failure_is_captured_without_crashing_runtime(self):
        supervisor = RuntimeSupervisor(settings=self.athena.settings)
        supervisor.scheduler = WorkerScheduler(supervisor.event_bus, supervisor.task_registry)
        supervisor.scheduler.register("failing", FailingWorker())
        supervisor.start(background=False)

        result = supervisor.run_once()

        self.assertEqual(result["workers_failed"], 1)
        self.assertEqual(supervisor.scheduler.failure_count, 1)
        self.assertEqual(supervisor.get_status()["state"], "idle")

    def test_learning_command_creates_session_and_candidates_without_confirmed_memory(self):
        before_long_term = self.athena.memory.count_real_long_term_memory()
        self.athena.llm_provider.reset_calls()

        response = self.athena.chat("Athena, aprender.")
        self.assertIn("Modo de aprendizado iniciado", response)
        self.assertEqual(self.athena.last_response_metadata["route"], "system")
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)
        self.assertIsNotNone(self.athena.learning_session_engine.active_session())

        self.athena.chat("A Athena deve ser uma arquitetura cognitiva, não uma LLM.")
        self.athena.runtime_supervisor.run_once()
        report = self.athena.chat("Athena, o que você aprendeu durante o aprender?")

        self.assertIn("Relatório do modo aprendizagem", report)
        self.assertIn("arquitetura cognitiva", report)
        self.assertGreaterEqual(self.athena.learning_candidate_store.count(status="candidate"), 1)
        self.assertEqual(self.athena.memory.count_real_long_term_memory(), before_long_term)

    def test_learning_candidate_approval_edit_reject_and_consolidation_are_explicit(self):
        self.athena.chat("Athena, aprender.")
        self.athena.chat("A LLM deve ser professora auxiliar, não cérebro central.")
        self.athena.runtime_supervisor.run_once()

        response = self.athena.chat("Aprovar aprendizado 1.")
        self.assertIn("aprovado", response)
        self.assertEqual(self.athena.learning_candidate_store.count(status="approved"), 1)

        response = self.athena.chat("Consolidar aprovados.")
        self.assertIn("Consolidei 1", response)
        self.assertEqual(self.athena.learning_candidate_store.count(status="promoted"), 1)
        memories = [row[1] for row in self.athena.memory.list_long_term_memory()]
        self.assertTrue(any("professora auxiliar" in item for item in memories))

        self.athena.chat("A Athena deve ter uma palheta de comandos cognitivos.")
        self.athena.runtime_supervisor.run_once()
        response = self.athena.chat("Editar aprendizado 1: A Athena deve ter uma palheta de comandos cognitivos supervisionada.")
        self.assertIn("atualizado", response)
        edited = self.athena.learning_candidate_store.resolve("1")
        self.assertIn("supervisionada", edited["content"])

        response = self.athena.chat("Rejeitar aprendizado 1.")
        self.assertIn("rejeitado", response)
        self.assertEqual(self.athena.learning_candidate_store.count(status="rejected"), 1)

    def test_full_presence_study_and_local_recall_cycle(self):
        response = self.athena.chat("Athena, iniciar runtime.")
        self.assertIn("Runtime iniciado", response)
        self.assertEqual(self.athena.runtime_supervisor.get_status()["state"], "idle")

        self.athena.chat("Athena, comando aprendizagem.")
        self.athena.chat("A Athena deve estudar o dia antes de consolidar memórias.")
        self.athena.chat("Conversas diárias devem ir para buffer temporário, não memória permanente.")
        self.athena.chat("LearningCandidate deve ficar separado de memória confirmada.")
        before_long_term = self.athena.memory.count_real_long_term_memory()

        self.athena.runtime_supervisor.run_once()
        self.assertGreaterEqual(self.athena.learning_candidate_store.count(status="candidate"), 2)
        self.assertEqual(self.athena.memory.count_real_long_term_memory(), before_long_term)

        report = self.athena.chat("Athena, relatório aprendizagem.")
        self.assertIn("Relatório do modo aprendizagem", report)

        self.athena.chat("Editar aprendizado 1: A Athena deve estudar o dia antes de consolidar memórias permanentes.")
        self.athena.chat("Aprovar candidatos 1 e 2.")
        self.athena.chat("Rejeitar candidato 3.")
        consolidated = self.athena.chat("Consolidar aprovados.")
        self.assertIn("Consolidei 2", consolidated)

        self.athena.llm_provider.reset_calls()
        learned = self.athena.chat("O que você aprendeu sobre memória diária?")
        self.assertIn("aprendi localmente", learned)
        self.assertIn("buffer temporário", learned)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

        paused = self.athena.chat("Athena, pausar runtime.")
        self.assertIn("Modo silêncio ativado", paused)
        self.assertTrue(self.athena.runtime_supervisor.get_status()["paused"])

        resumed = self.athena.chat("Athena, retomar runtime.")
        self.assertIn("Retomei", resumed)
        self.assertFalse(self.athena.runtime_supervisor.get_status()["paused"])

        stopped = self.athena.chat("Athena, desligar runtime.")
        self.assertIn("Runtime encerrado com segurança", stopped)
        self.assertEqual(self.athena.runtime_supervisor.get_status()["state"], "stopped")

    def test_study_command_uses_day_buffer_and_local_report(self):
        before = self.athena.memory.count_real_long_term_memory()
        self.athena.chat("A Athena deve estudar o dia antes de consolidar memórias.")
        self.athena.chat("Conversas diárias devem ir para buffer temporário, não memória permanente.")

        response = self.athena.chat("Athena, comando estudar.")
        self.assertIn("Estudei o material", response)
        self.assertGreaterEqual(self.athena.learning_candidate_store.count(status="candidate"), 1)
        self.assertEqual(self.athena.memory.count_real_long_term_memory(), before)

        self.athena.llm_provider.reset_calls()
        report = self.athena.chat("Athena, o que você achou interessante?")
        self.assertIn("Relatório do estudo diário", report)
        self.assertIn("buffer temporário", report)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_runtime_status_and_diagnostic_are_local_commands(self):
        self.athena.runtime_supervisor.start(background=False)
        self.athena.llm_provider.reset_calls()

        status = self.athena.chat("Athena, status.")
        self.assertIn("runtime", status)
        self.assertIn("aprendizado", status)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

        diagnostic = self.athena.chat("Athena, comando diagnóstico.")
        self.assertIn("Diagnóstico local do runtime", diagnostic)
        self.assertEqual(self.athena.last_response_metadata["llm_calls"], 0)

    def test_chat_still_works_when_runtime_is_not_started(self):
        self.assertEqual(self.athena.runtime_supervisor.get_status()["state"], "offline")
        response = self.athena.chat("Quem é você?")
        self.assertIn("Eu sou Athena", response)


if __name__ == "__main__":
    unittest.main()
