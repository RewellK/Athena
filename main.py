from brain.orchestrator import Athena


def main():
    athena = Athena()

    print("Athena V12.3 — Natural Conversation, Performance & GUI Polish")
    print("Digite 'sair' para encerrar.")
    print("Bootstrap automático ativo.")
    print("Conversation-first ativo com respostas naturais, métricas e caminho rápido.")

    while True:
        user_input = input("\nVocê: ")

        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Athena: Até logo.")
            break

        response = athena.chat(user_input)
        print(f"Athena: {response}")


if __name__ == "__main__":
    main()
