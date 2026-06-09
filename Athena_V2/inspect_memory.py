from memory.database import MemoryDB

db = MemoryDB()

print("\n=== CONCEITOS ===\n")

for concept in db.list_concepts():
    print(concept[0])

print("\n=== DEFINIÇÕES ===\n")

for concept, meaning in db.list_definitions():
    print(f"{concept} -> {meaning}")