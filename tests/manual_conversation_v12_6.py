import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.test_v12_5 import make_athena  # noqa: E402


CONVERSATIONS = [
    (
        "Conversation 1 — Fernanda messy query",
        [
            "Oii, boa noite, tudo bem com você?",
            "Perfeito, você sabe que é a fernanda?",
            "quero saber oq você sabe sobre ela.",
            "quero que me fale sobre a Fernadna",
            "Fernanda é minha namorada.",
            "quem é ela?",
            "me fala dela",
        ],
    ),
    (
        "Conversation 2 — Francisco, topic switch, confirmation",
        [
            "Meu pai é Francisco.",
            "legal, e quem é você?",
            "sim",
            "quem é meu pai?",
            "quem é Francisco?",
            "ele gosta de carro.",
            "o que você sabe sobre ele?",
        ],
    ),
    (
        "Conversation 3 — Capabilities, limitations, tools",
        [
            "Hoje meu dia foi muito bom, oq vc faz mesmo?",
            "quais coisa você consegue fazer?",
            "e oq você ainda não consegue?",
            "qual a previsão do clima de amanhã?",
            "quais são as notícias de hoje?",
            "oq você não entendeu?",
        ],
    ),
    (
        "Conversation 4 — Athena relationship",
        [
            "Você não é minha assistente, você é minha amiga.",
            "eu gosto muito de você, sabia?",
            "quem é você pra mim?",
        ],
    ),
]

LLM_UNAVAILABLE_MESSAGES = [
    "quem é Fernanda?",
    "Fernanda é minha namorada.",
    "posso te ensinar?",
    "o que você pode fazer?",
    "quem é você?",
]


def _metadata_line(metadata):
    return (
        f"route={metadata.get('route')} | "
        f"target={metadata.get('target', '')} | "
        f"confidence={metadata.get('confidence', '')} | "
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


def _record(section, user, athena, metadata):
    return {
        "section": section,
        "user": user,
        "athena": athena,
        "metadata": dict(metadata),
    }


def _by_user(records):
    return {record["user"]: record for record in records}


def _assert_route(record, route, target=None, llm_calls=None):
    metadata = record["metadata"]
    if metadata.get("route") != route:
        raise AssertionError(f"{record['user']} expected route={route}, got {metadata.get('route')}")
    if target is not None and metadata.get("target") != target:
        raise AssertionError(f"{record['user']} expected target={target}, got {metadata.get('target')}")
    if llm_calls is not None and metadata.get("llm_calls") != llm_calls:
        raise AssertionError(f"{record['user']} expected llm_calls={llm_calls}, got {metadata.get('llm_calls')}")


def _assert_no_bad_fallback(record):
    text = record["athena"]
    if "Não entendi com segurança" in text:
        raise AssertionError(f"{record['user']} fell into generic unknown fallback")


def _assert_critical(records):
    by = _by_user(records)

    _assert_route(by["Oii, boa noite, tudo bem com você?"], "small_talk", llm_calls=0)
    _assert_no_bad_fallback(by["Oii, boa noite, tudo bem com você?"])

    messy = by["Perfeito, você sabe que é a fernanda?"]
    _assert_route(messy, "world_query", target="Fernanda", llm_calls=0)
    _assert_no_bad_fallback(messy)
    if "não sinto" in messy["athena"].lower():
        raise AssertionError("third-party entity query mentioned Athena feelings")

    pronoun = by["quero saber oq você sabe sobre ela."]
    _assert_route(pronoun, "world_query", target="Fernanda", llm_calls=0)
    _assert_no_bad_fallback(pronoun)

    typo = by["quero que me fale sobre a Fernadna"]
    _assert_route(typo, "world_query", target="Fernanda", llm_calls=0)
    _assert_no_bad_fallback(typo)

    learning = by["Fernanda é minha namorada."]
    _assert_route(learning, "learning", target="Fernanda")
    _assert_no_bad_fallback(learning)

    recall = by["quem é ela?"]
    _assert_route(recall, "world_query", target="Fernanda", llm_calls=0)
    if not _contains(recall["athena"], "fernanda", "namorada"):
        raise AssertionError("pronoun recall after learning did not describe Fernanda")

    about_her = by["me fala dela"]
    _assert_route(about_her, "world_query", target="Fernanda", llm_calls=0)
    if not _contains(about_her["athena"], "fernanda", "namorada"):
        raise AssertionError("dela recall after learning did not describe Fernanda")

    father = by["Meu pai é Francisco."]
    _assert_route(father, "learning", target="Francisco")
    _assert_no_bad_fallback(father)

    identity = by["legal, e quem é você?"]
    _assert_route(identity, "identity", target="Athena", llm_calls=0)
    if "Athena" not in identity["athena"]:
        raise AssertionError("identity answer did not identify Athena")

    yes = by["sim"]
    if yes["metadata"].get("route") not in {"pending_confirmation", "conversation"}:
        raise AssertionError("sim was not handled as pending confirmation or local acknowledgement")
    if yes["metadata"].get("llm_calls") != 0:
        raise AssertionError("sim without pending should not run heavy pipeline")

    my_father = by["quem é meu pai?"]
    _assert_route(my_father, "world_query", target="Meu Pai", llm_calls=0)
    if not _contains(my_father["athena"], "francisco", "pai"):
        raise AssertionError("quem é meu pai did not answer Francisco")

    francisco = by["quem é Francisco?"]
    _assert_route(francisco, "world_query", target="Francisco", llm_calls=0)
    if not _contains(francisco["athena"], "francisco", "pai"):
        raise AssertionError("quem é Francisco did not answer father relation")

    car_learning = by["ele gosta de carro."]
    _assert_route(car_learning, "learning", target="Francisco")

    about_him = by["o que você sabe sobre ele?"]
    _assert_route(about_him, "world_query", target="Francisco", llm_calls=0)
    if not _contains(about_him["athena"], "francisco", "carro"):
        raise AssertionError("ele recall did not include Francisco and car")

    day_capability = by["Hoje meu dia foi muito bom, oq vc faz mesmo?"]
    _assert_route(day_capability, "capability", target="Athena", llm_calls=0)
    if not _contains(day_capability["athena"], "dia foi bom", "posso"):
        raise AssertionError("multi-intent capability answer did not acknowledge the good day")

    _assert_route(by["quais coisa você consegue fazer?"], "capability", target="Athena", llm_calls=0)

    limitations = by["e oq você ainda não consegue?"]
    _assert_route(limitations, "capability", target="Athena", llm_calls=0)
    if not _contains(limitations["athena"], "ainda não consigo"):
        raise AssertionError("limitations query did not answer limitations")

    _assert_route(by["qual a previsão do clima de amanhã?"], "external_information", llm_calls=0)
    _assert_route(by["quais são as notícias de hoje?"], "external_information", llm_calls=0)

    unknown = by["oq você não entendeu?"]
    _assert_route(unknown, "system", target="last_unknown", llm_calls=0)
    if "Pode me explicar de outro jeito?" in unknown["athena"]:
        raise AssertionError("unknown recovery repeated fallback")

    friend = by["Você não é minha assistente, você é minha amiga."]
    _assert_route(friend, "learning", target="Athena")
    if not _contains(friend["athena"], "não sinto"):
        raise AssertionError("Athena relationship did not preserve non-human feeling boundary")

    like = by["eu gosto muito de você, sabia?"]
    _assert_route(like, "learning", target="Athena")
    if not _contains(like["athena"], "não sinto"):
        raise AssertionError("Athena affection learning did not preserve non-human feeling boundary")

    relationship = by["quem é você pra mim?"]
    _assert_route(relationship, "identity", target="Athena", llm_calls=0)
    if not _contains(relationship["athena"], "amiga", "não sinto"):
        raise AssertionError("relationship identity did not use learned relationship")


def _assert_llm_unavailable(records):
    by = _by_user(records)
    _assert_route(by["quem é Fernanda?"], "world_query", target="Fernanda", llm_calls=0)
    _assert_route(by["Fernanda é minha namorada."], "learning", target="Fernanda", llm_calls=0)
    _assert_no_bad_fallback(by["Fernanda é minha namorada."])
    _assert_route(by["posso te ensinar?"], "teach_intent", target="Athena", llm_calls=0)
    _assert_route(by["o que você pode fazer?"], "capability", target="Athena", llm_calls=0)
    _assert_route(by["quem é você?"], "identity", target="Athena", llm_calls=0)


def _run_conversations():
    records = []
    with tempfile.TemporaryDirectory() as temp_dir:
        athena = make_athena(Path(temp_dir))
        try:
            for section, messages in CONVERSATIONS:
                for message in messages:
                    response = athena.chat(message)
                    records.append(_record(section, message, response, athena.last_response_metadata))
        finally:
            athena.memory.close()
    _assert_critical(records)
    return records


def _run_llm_unavailable():
    records = []
    with tempfile.TemporaryDirectory() as temp_dir:
        athena = make_athena(Path(temp_dir))
        athena.settings.values["useLLM"] = False
        try:
            for message in LLM_UNAVAILABLE_MESSAGES:
                response = athena.chat(message)
                records.append(_record("Conversation 5 — LLM unavailable", message, response, athena.last_response_metadata))
        finally:
            athena.memory.close()
    _assert_llm_unavailable(records)
    return records


def run():
    records = _run_conversations() + _run_llm_unavailable()
    current_section = None
    for record in records:
        if record["section"] != current_section:
            current_section = record["section"]
            print(f"## {current_section}")
            print()
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
