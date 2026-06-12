from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_v12_5 import make_athena


def show(label, athena, message):
    response = athena.chat(message)
    metadata = athena.last_response_metadata
    print(f"Usuário: {message}")
    print(f"Athena: {response}")
    print(
        "metadata: "
        f"route={metadata.get('route')} | "
        f"domain={metadata.get('external_domain')} | "
        f"source_status={metadata.get('source_status')} | "
        f"source_proposal={metadata.get('source_proposal')} | "
        f"llm_calls={metadata.get('llm_calls')} | "
        f"duration_ms={metadata.get('duration_ms')}"
    )
    pending = getattr(athena, "pending_source_proposal", None)
    if pending:
        print(f"pendência: {pending.get('summary')} | status={pending.get('status')}")
    print()
    return response


def main():
    with TemporaryDirectory() as tmp:
        athena = make_athena(Path(tmp))
        try:
            print("=== Manual Sources V12.8 ===")
            show("veículos", athena, "Athena, quanto custa um Civic 2020?")
            show("aprovação", athena, "sim")
            print("Fontes cadastradas:")
            for source in athena.source_manager.registry.list_sources():
                print(
                    f"- {source['source_id']} | domain={source['domain']} | "
                    f"status={source['status']} | enabled={source['enabled']} | "
                    f"validation={source['validation_status']}"
                )
            print()
            show("notícias", athena, "Quais são as notícias de hoje?")
            print("A Athena não consultou internet real, não usou fonte candidata como evidência e não inventou fatos externos.")
        finally:
            athena.memory.close()


if __name__ == "__main__":
    main()
