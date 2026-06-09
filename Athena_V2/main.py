
from brain.orchestrator import Athena

athena = Athena()

print("Athena V2 acordou.")
print("Diga 'sair' para encerrar.")

while True:
    msg = input("\nVocê: ")
    if msg.lower() == "sair":
        break
    print("\nAthena:", athena.chat(msg))
