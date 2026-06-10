from brain.orchestrator import Athena


def main():
    athena = Athena()

    print("Athena V12 — Desktop + Self Code Awareness + Git Read Awareness")
    print("Digite 'sair' para encerrar.")
    print("Bootstrap automático ativo.")
    print("Orchestrator em modo lockdown: terminal e GUI usam o mesmo Athena Core.")

    while True:
        user_input = input("\nVocê: ")

        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Athena: Até logo.")
            break

        response = athena.chat(user_input)
        print(f"Athena: {response}")


if __name__ == "__main__":
    main()
