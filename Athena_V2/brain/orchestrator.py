import json

from memory.database import MemoryDB
from brain.curiosity import generate_question


class Athena:

    def __init__(self):

        self.memory = MemoryDB()

        with open(
            "personality/identity.json",
            "r",
            encoding="utf-8"
        ) as f:

            self.identity = json.load(f)

    def chat(self, user_input):

        # Salva toda conversa
        self.memory.save_memory(
            "conversation",
            user_input
        )

        lower = user_input.lower().strip()

        # ==========================
        # APRENDIZADO AUTOMÁTICO
        # ==========================

        if " é " in lower:

            partes = lower.split(" é ", 1)

            conceito = partes[0].strip()

            significado = partes[1].strip()

            self.memory.save_definition(
                conceito,
                significado
            )

            return (
                f"Entendi.\n"
                f"Aprendi que "
                f"{conceito} significa "
                f"{significado}"
            )

        # ==========================
        # IDENTIDADE
        # ==========================

        if lower in [
            "quem é você",
            "quem é voce",
            "quem é a athena",
            "quem é athena"
        ]:

            return (
                f"Eu sou {self.identity['name']}.\n"
                f"Fui criada por "
                f"{self.identity['creator']}.\n"
                f"Meu propósito é "
                f"{self.identity['purpose']}."
            )

        if lower == "quem é rewell":

            return (
                self.memory.get_definition(
                    "rewell"
                )
                or
                "Ainda não sei quem é Rewell."
            )

        if (
            lower == "qual seu propósito"
            or
            lower == "qual o seu propósito"
        ):

            return self.identity["purpose"]

        # ==========================
        # CONSULTA DIRETA
        # ==========================

        meaning = self.memory.get_definition(
            lower
        )

        if meaning:

            return (
                f"{lower} significa:\n\n"
                f"{meaning}"
            )

        # ==========================
        # EXTRAÇÃO DE CONCEITOS
        # ==========================

        concepts = self.memory.extract_concepts(
            user_input
        )

        for concept in concepts:

            meaning = self.memory.get_definition(
                concept
            )

            if meaning:

                return (
                    f"Eu já sei que "
                    f"{concept} significa:\n\n"
                    f"{meaning}"
                )

            self.memory.save_concept(
                concept
            )

        # ==========================
        # CURIOSIDADE
        # ==========================

        return generate_question(
            concepts
        )