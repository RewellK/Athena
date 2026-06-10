from brain.orchestrator import Athena


def main():
    athena = Athena()

    print("Athena V11 — Agency & Action Foundation Lockdown")
    print("Digite 'sair' para encerrar.")
    print("Bootstrap automático ativo.")
    print("Orchestrator em modo lockdown: coordena, delega e retorna; não interpreta significado.")

    while True:
        user_input = input("\nVocê: ")

        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Athena: Até logo.")
            break

        response = athena.chat(user_input)
        print(f"Athena: {response}")


if __name__ == "__main__":
    main()
