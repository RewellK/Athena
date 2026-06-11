import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.test_v12_5 import make_athena  # noqa: E402


MESSAGES = [
    "boa noite, tudo sim, e com você?",
    "que legal, consegue me falar quem é a Fernanda?",
    "Fernanda é minha namorada.",
    "quem é Fernanda?",
    "Meu pai é Francisco.",
    "ótimo, quem é você?",
    "sim",
    "Quem é Francisco?",
    "Hoje meu dia foi muito bom, o que você pode fazer?",
    "o que você não entendeu?",
    "Qual a previsão do clima hoje?",
    "Você não é minha assistente, você é minha amiga.",
]


def _metadata_line(metadata):
    return (
        f"route={metadata.get('route')} | "
        f"target={metadata.get('target', '')} | "
        f"llm_calls={metadata.get('llm_calls', metadata.get('llm_call_count', 0))} | "
        f"duration_ms={metadata.get('duration_ms', metadata.get('total_duration_ms', 0))} | "
        f"used_world_model={metadata.get('used_world_model')} | "
        f"used_memory={metadata.get('used_memory')} | "
        f"used_llm={metadata.get('used_llm')} | "
        f"pending_confirmation={metadata.get('pending_confirmation')}"
    )


def _contains(text, *needles):
    lowered = str(text or "").lower()
    return all(str(needle).lower() in lowered for needle in needles)


def _assert_critical(records):
    by_message = {record["user"]: record for record in records}

    entity_unknown = by_message["que legal, consegue me falar quem é a Fernanda?"]
    if entity_unknown["metadata"].get("route") != "world_query" or "Não entendi" in entity_unknown["athena"]:
        raise AssertionError("entity query before learning fell into an invalid route or unknown response")

    learning = by_message["Fernanda é minha namorada."]
    if learning["metadata"].get("route") != "learning" or "Não entendi" in learning["athena"]:
        raise AssertionError("learning candidate fell into unknown")

    entity_known = by_message["quem é Fernanda?"]
    if entity_known["metadata"].get("route") != "world_query" or not _contains(entity_known["athena"], "fernanda", "namorada"):
        raise AssertionError("known entity query did not recall Fernanda locally")

    identity = by_message["ótimo, quem é você?"]
    if identity["metadata"].get("route") != "identity" or not _contains(identity["athena"], "athena"):
        raise AssertionError("self identity did not answer locally")

    father = by_message["Quem é Francisco?"]
    if father["metadata"].get("route") != "world_query" or not _contains(father["athena"], "francisco", "pai"):
        raise AssertionError("known entity query did not recall Francisco")

    capability = by_message["Hoje meu dia foi muito bom, o que você pode fazer?"]
    if capability["metadata"].get("route") != "capability" or not _contains(capability["athena"], "posso"):
        raise AssertionError("capability query did not route to CapabilityEngine")

    unknown_recovery = by_message["o que você não entendeu?"]
    if unknown_recovery["metadata"].get("intent") != "unknown_recovery" or "Pode me explicar de outro jeito?" in unknown_recovery["athena"]:
        raise AssertionError("unknown recovery repeated the fallback loop")

    external = by_message["Qual a previsão do clima hoje?"]
    if external["metadata"].get("route") != "external_information" or not _contains(external["athena"], "ferramenta", "tempo real"):
        raise AssertionError("external current-information request was not handled safely")

    relationship = by_message["Você não é minha assistente, você é minha amiga."]
    if relationship["metadata"].get("route") != "learning" or not _contains(relationship["athena"], "não sinto"):
        raise AssertionError("relationship learning did not preserve the non-human feeling boundary")


def run():
    records = []
    with tempfile.TemporaryDirectory() as temp_dir:
        athena = make_athena(Path(temp_dir))
        try:
            for message in MESSAGES:
                response = athena.chat(message)
                metadata = dict(athena.last_response_metadata)
                records.append({"user": message, "athena": response, "metadata": metadata})
        finally:
            athena.memory.close()

    _assert_critical(records)

    for record in records:
        print("Usuário:")
        print(record["user"])
        print()
        print("Athena:")
        print(record["athena"])
        print()
        print("Metadata:")
        print(_metadata_line(record["metadata"]))
        print()
        print("---")


if __name__ == "__main__":
    run()
