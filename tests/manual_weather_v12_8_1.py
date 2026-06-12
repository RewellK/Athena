from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sources.evidence_engine import EvidenceEngine
from sources.external_research_worker import AsyncExternalResearchWorker
from sources.source_manager import SourceManager
from sources.source_registry import SourceRegistry
from tests.test_source_manager import MockWeatherConnector
from tests.test_v12_5 import make_athena


class FailingWeatherConnector:
    def fetch(self, *_args, **_kwargs):
        raise RuntimeError("falha mockada da fonte de clima")


def show(athena, message):
    response = athena.chat(message)
    metadata = athena.last_response_metadata
    print(f"Usuário: {message}")
    print(f"Athena: {response}")
    print(
        "metadata: "
        f"route={metadata.get('route')} | "
        f"domain={metadata.get('external_domain')} | "
        f"source_status={metadata.get('source_status')} | "
        f"source_id={metadata.get('source_id')} | "
        f"evidence_id={metadata.get('evidence_id')} | "
        f"job_status={metadata.get('external_research_job_status')} | "
        f"llm_calls={metadata.get('llm_calls')} | "
        f"duration_ms={metadata.get('duration_ms')}"
    )
    print()


def configure_weather(athena, connector):
    athena.settings.values["weatherDefaultLocation"] = {
        "city": "Embu das Artes",
        "state": "SP",
        "country": "Brasil",
        "latitude": -23.6489,
        "longitude": -46.8522,
    }
    evidence = EvidenceEngine()
    worker = AsyncExternalResearchWorker(
        evidence_engine=evidence,
        connectors={"weather_open_meteo": connector},
        timeout_seconds=3,
    )
    athena.source_manager = SourceManager(
        settings=athena.settings,
        registry=SourceRegistry(),
        evidence_engine=evidence,
        worker=worker,
    )


def main():
    with TemporaryDirectory() as tmp:
        print("=== Manual Weather V12.8.1 ===")

        case_dir = Path(tmp) / "missing_location"
        case_dir.mkdir()
        athena = make_athena(case_dir)
        try:
            print("--- Cenário 1: sem localização ---")
            show(athena, "Qual a previsão do clima amanhã?")
        finally:
            athena.memory.close()

        case_dir = Path(tmp) / "weather_ok"
        case_dir.mkdir()
        athena = make_athena(case_dir)
        try:
            print("--- Cenário 2: fonte configurada + localização mockada ---")
            configure_weather(athena, MockWeatherConnector())
            show(athena, "Qual a previsão do clima amanhã?")
        finally:
            athena.memory.close()

        case_dir = Path(tmp) / "weather_fail"
        case_dir.mkdir()
        athena = make_athena(case_dir)
        try:
            print("--- Cenário 3: fonte falha ---")
            configure_weather(athena, FailingWeatherConnector())
            show(athena, "Qual a previsão do clima amanhã?")
        finally:
            athena.memory.close()


if __name__ == "__main__":
    main()
