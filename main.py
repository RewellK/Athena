from brain.orchestrator import Athena


def main():
    athena = Athena()

    print("Athena V12.2 — Conversational Maturity & Core Stabilization")
    print("Digite 'sair' para encerrar.")
    print("Bootstrap automático ativo.")
    print("Conversation-first ativo: terminal e GUI usam o mesmo Athena Core.")

    while True:
        user_input = input("\nVocê: ")

        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Athena: Até logo.")
            break

        response = athena.chat(user_input)
        print(f"Athena: {response}")


if __name__ == "__main__":
    main()
