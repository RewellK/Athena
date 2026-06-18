import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_v12_5 import make_athena


def run():
    transcript = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        athena = make_athena(root)
        try:
            turns = [
                "Athena, iniciar runtime.",
                "Athena, qual seu status?",
                "Athena, comando aprendizagem.",
                "A Athena deve ser uma arquitetura cognitiva, não uma LLM.",
                "A LLM deve ser professora auxiliar, não cérebro central.",
                "A Athena deve estudar o dia antes de consolidar memórias.",
                "Conversas diárias devem ir para buffer temporário, não memória permanente.",
                "LearningCandidate deve ficar separado de memória confirmada.",
            ]
            for message in turns:
                response = athena.chat(message)
                transcript.append(("Usuário", message))
                transcript.append(("Athena", response))

            cycle = athena.runtime_supervisor.run_once()
            transcript.append(("Sistema", f"RuntimeSupervisor.run_once(): {cycle}"))

            turns = [
                "Athena, relatório aprendizagem.",
                "Editar aprendizado 1: A Athena deve estudar o dia antes de consolidar memórias permanentes.",
                "Aprovar candidatos 1 e 4.",
                "Rejeitar candidato 5.",
                "Consolidar aprovados.",
                "O que você aprendeu sobre memória diária?",
                "Athena, comando estudar.",
                "Athena, o que você achou interessante?",
                "Athena, pausar runtime.",
                "Athena, retomar runtime.",
                "Athena, comando diagnóstico.",
                "Athena, desligar runtime.",
            ]
            for message in turns:
                response = athena.chat(message)
                transcript.append(("Usuário", message))
                transcript.append(("Athena", response))
            athena.memory.close()

            transcript.append(("Sistema", "Athena fechada e reiniciada usando o mesmo knowledge.db."))
            reopened = make_athena(root)
            try:
                reopened.llm_provider.reset_calls()
                message = "O que você aprendeu sobre conversas diárias?"
                response = reopened.chat(message)
                transcript.append(("Usuário", message))
                transcript.append(("Athena", response))
                transcript.append(("Sistema", f"LLM calls na recuperação pós-restart: {reopened.last_response_metadata.get('llm_calls')}"))

                rows = reopened.memory.list_long_term_memory_with_metadata()
                if rows:
                    memory_id = rows[0][0]
                    metadata = dict(rows[0][5])
                    past = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
                    metadata["created_at"] = past
                    metadata["promoted_at"] = past
                    reopened.memory.conn.execute(
                        "UPDATE long_term_memory SET created_at = ?, metadata_json = ? WHERE id = ?",
                        (past, json.dumps(metadata, ensure_ascii=False, sort_keys=True), memory_id),
                    )
                    reopened.memory.conn.commit()
                reopened.day_memory_buffer.discard()
                for candidate in reopened.learning_candidate_store.list(limit=100000):
                    reopened.learning_candidate_store.update_status(candidate.get("id"), "discarded")
                transcript.append(("Sistema", "Simulado +7 dias; buffer diário descartado e candidatos locais descartados."))

                reopened.llm_provider.reset_calls()
                message = "O que você sabe sobre memória diária?"
                response = reopened.chat(message)
                transcript.append(("Usuário", message))
                transcript.append(("Athena", response))
                transcript.append(("Sistema", f"LLM calls na recuperação multidia: {reopened.last_response_metadata.get('llm_calls')}"))
            finally:
                reopened.memory.close()
        finally:
            try:
                athena.memory.close()
            except Exception:
                pass
    return transcript


if __name__ == "__main__":
    for speaker, text in run():
        print(f"{speaker}: {text}")
