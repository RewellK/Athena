from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reflection.reflection_engine import ReflectionEngine
from reflection.reflection_store import ReflectionStore


class LocalSettings:
    def get(self, key, default=None):
        values = {
            "reflectionEnabled": True,
            "reflectionUseLlmResponse": False,
            "reflectionSlowRecallMs": 2500,
        }
        return values.get(key, default)


def print_event(event):
    print(f"Reflection: issue_type={event.issue_type} | severity={event.severity}")
    print(f"Modulo suspeito: {event.suspected_module}")
    print(f"Falha detectada: {event.explanation}")
    print(f"Melhoria sugerida: {event.suggestion}")
    for test in event.suggested_tests:
        print(f"Teste sugerido: {test}")
    print(f"Revisao humana obrigatoria: {event.requires_human_review}")
    print()


def main():
    with TemporaryDirectory() as tmp:
        engine = ReflectionEngine(
            memory=None,
            identity={"name": "Athena", "creator": "Rewell"},
            store=ReflectionStore(path=str(Path(tmp) / "reflection_events.jsonl")),
            settings=LocalSettings(),
        )

        transcript = [
            {
                "user": "quem é Fernanda?",
                "athena": "Eu ainda não sinto como um humano, mas vou tratar essa informação com cuidado.",
                "metadata": {
                    "route": "world_query",
                    "intent": "entity_query",
                    "target": "Fernanda",
                    "used_world_model": True,
                    "llm_calls": 0,
                },
            },
            {
                "user": "quero saber o que você sabe sobre ela",
                "athena": "Não entendi com segurança o que você quer agora. Pode me explicar de outro jeito?",
                "metadata": {
                    "route": "unknown",
                    "intent": "unknown",
                    "target": "",
                    "recent_entities": ["Fernanda"],
                    "needs_clarification": True,
                    "llm_calls": 0,
                },
            },
            {
                "user": "oq você pode fazer?",
                "athena": "Eu posso conversar, lembrar e consultar meu World Model.",
                "metadata": {
                    "route": "capability",
                    "intent": "capability_query",
                    "target": "Athena",
                    "llm_calls": 2,
                },
            },
        ]

        print("=== Manual Reflection V12.7 ===")
        for item in transcript:
            print(f"Usuario: {item['user']}")
            print(f"Athena: {item['athena']}")
            events = engine.observe_turn(item["user"], item["athena"], metadata=item["metadata"])
            if not events:
                print("Reflection: sem falha critica detectada.\n")
            for event in events:
                print_event(event)

        print("Pergunta ao ReflectionEngine: o que você acha que precisa melhorar?")
        print(engine.respond("o que você acha que precisa melhorar?"))


if __name__ == "__main__":
    main()
