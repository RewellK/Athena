import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_v12_5 import make_athena


def show(athena, message):
    response = athena.chat(message)
    metadata = athena.last_response_metadata
    print(f"\nUSUARIO: {message}")
    print(f"ATHENA: {response}")
    print(
        "META: "
        f"route={metadata.get('route')} | "
        f"domain={metadata.get('external_domain')} | "
        f"source_status={metadata.get('source_status')} | "
        f"gap={metadata.get('capability_gap_type')} | "
        f"proposal={metadata.get('module_proposal_title')} | "
        f"llm_calls={metadata.get('llm_calls')} | "
        f"duration_ms={metadata.get('duration_ms')}"
    )
    return response


def main():
    print("=== Manual V12.9 Risk Closure ===")
    with tempfile.TemporaryDirectory() as tmp:
        athena = make_athena(Path(tmp))
        try:
            show(athena, "Qual a previsão do clima amanhã?")
            show(athena, "Minha localização é São Paulo, SP.")
            show(athena, "Qual localização você tem salva?")
            show(athena, "Qual a previsão do clima amanhã?")
            show(athena, "Sim")
            show(athena, "Apague minha localização.")
            show(athena, "Qual localização você tem salva?")
            show(athena, "Quanto custa um Civic 2020?")
            show(athena, "Sim")
            show(athena, "Quanto custa um Corolla 2021?")
            show(athena, "Sim")
            show(athena, "Athena, busque jurisprudência recente")
            show(athena, "Não")
            show(athena, "crie uma proposta de melhoria para painel visual de aprendizado")
            show(athena, "Tem algo que você precisa melhorar?")
            show(athena, "Quais módulos você acha que precisa?")
            show(athena, "Você está pronta para V13-pre?")

            proposals = athena.source_manager.list_module_proposals()
            print("\nPROPOSTAS:")
            for proposal in proposals:
                print(
                    f"- {proposal.get('title')} | domain={proposal.get('domain')} | "
                    f"status={proposal.get('status')} | occurrences={proposal.get('occurrence_count')}"
                )
        finally:
            athena.memory.close()


if __name__ == "__main__":
    main()
