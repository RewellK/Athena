import tempfile
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_v12_5 import make_athena


class MockWeatherConnector:
    def fetch(self, query, timeout_seconds=None, request=None, source=None):
        location = request["location"]
        return {
            "source_id": "weather.open_meteo",
            "location_name": location["name"],
            "forecast_date": "2026-06-18",
            "summary": "previsão de céu parcialmente nublado, mínima de 15°C e máxima de 24°C.",
            "temperature_min": 15,
            "temperature_max": 24,
            "precipitation_probability": 20,
            "weather_code": 2,
            "raw": {"mock": True},
            "endpoint": "https://api.open-meteo.com/v1/forecast",
        }


def print_turn(athena, user_message):
    started_at = time.perf_counter()
    response = athena.chat(user_message)
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    metadata = athena.last_response_metadata
    print(f"\nUSUARIO: {user_message}")
    print(f"ATHENA: {response}")
    print(
        "META: "
        f"route={metadata.get('route')} | "
        f"target={metadata.get('target')} | "
        f"domain={metadata.get('external_domain')} | "
        f"llm_calls={metadata.get('llm_calls')} | "
        f"used_memory={metadata.get('used_memory')} | "
        f"used_world_model={metadata.get('used_world_model')} | "
        f"used_source={metadata.get('used_source')} | "
        f"used_research_strategy={metadata.get('used_research_strategy')} | "
        f"evidence_id={metadata.get('evidence_id')} | "
        f"reflection_events={metadata.get('reflection_events')} | "
        f"duration_ms={metadata.get('duration_ms', elapsed_ms)}"
    )


def main():
    with tempfile.TemporaryDirectory() as tmp:
        athena = make_athena(Path(tmp))
        athena.source_manager.worker.connectors["weather_open_meteo"] = MockWeatherConnector()
        try:
            messages = [
                "Oi",
                "Quem é você?",
                "Quem sou eu?",
                "O que você pode fazer?",
                "Fernanda é minha namorada.",
                "Quem é Fernanda?",
                "me fala dela",
                "O que você sabe sobre ela?",
                "Meu pai é Francisco.",
                "Ele gosta de carro.",
                "O que você sabe sobre ele?",
                "Qual a previsão do clima amanhã?",
            ]
            for message in messages:
                print_turn(athena, message)

            athena.settings.values["weatherDefaultLocation"] = {
                "city": "São Paulo",
                "state": "SP",
                "country": "Brasil",
                "latitude": -23.5505,
                "longitude": -46.6333,
            }
            print_turn(athena, "Qual a previsão do clima amanhã em São Paulo?")

            for message in [
                "Quanto custa um Civic 2020?",
                "Sim",
                "Quais fontes você conhece?",
                "Quais fontes estão pendentes?",
                "O que você aprendeu pesquisando?",
                "Quais estratégias de pesquisa você conhece?",
                "O que você lembra sobre Fernanda?",
                "Quais memórias estão pendentes?",
                "Tem algo que você precisa melhorar?",
                "Corrige isso: quando eu disser “me fala dela”, quero que você entenda como consulta sobre a última entidade citada.",
                "mostre exemplos de treino pendentes",
            ]:
                print_turn(athena, message)

            pending_examples = athena.linguistic_learning_workbench.list_examples(status="pending_human_review")
            if pending_examples:
                print_turn(athena, f"aprovar exemplo {pending_examples[0]['id']}")

            for message in [
                "mostre padrões linguísticos aprendidos",
                "você já consegue fazer isso sem LLM?",
                "quais coisas ainda dependem da LLM?",
                "mostre insights pendentes",
                "quais módulos você acha que precisa?",
                "Você está pronta para V13?",
            ]:
                print_turn(athena, message)
        finally:
            athena.memory.close()


if __name__ == "__main__":
    main()
