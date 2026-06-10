from brain.orchestrator import Athena


def main():
    athena = Athena()

    print("Athena V12.4 — LLM-Guided Intent & Target Resolution")
    print("Digite 'sair' para encerrar.")
    print("Bootstrap automático ativo.")
    print("Intent resolution LLM-first ativo. Core decide; LLM interpreta linguagem.")

    while True:
        user_input = input("\nVocê: ")

        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Athena: Até logo.")
            break

        response = athena.chat(user_input)
        print(f"Athena: {response}")


if __name__ == "__main__":
    main()
