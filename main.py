from brain.orchestrator import Athena
from runtime.process_lease import foreground_session, close_core
from pathlib import Path
import os


def _main():
    athena = Athena()
    athena.start_foreground_presence()

    print("Athena — presença local supervisionada")
    print("Digite 'sair' para encerrar.")
    print("Bootstrap automático ativo.")
    print("Execução OpenJarvis ativa. Identidade, memória e ferramentas pertencem à Athena.")

    try:
        while True:
            try:
                user_input = input("\nVocê: ")
            except (EOFError, KeyboardInterrupt):
                break

            if user_input.lower() in ["sair", "exit", "quit"]:
                print("Athena: Até logo.")
                break

            response = athena.chat(user_input)
            print(f"Athena: {response}")
    finally:
        close_core(athena)


def main():
    os.chdir(Path(__file__).resolve().parent)
    os.umask(0o077)
    with foreground_session():
        _main()


if __name__ == "__main__":
    main()

# Backward-compatible entry used by athena.py.
run = main
