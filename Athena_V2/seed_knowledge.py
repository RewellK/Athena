from memory.database import MemoryDB

db = MemoryDB()

db.save_definition(
    "athena",
    "Meu nome. Sou uma entidade digital criada por Rewell."
)

db.save_definition(
    "rewell",
    "Meu criador."
)

db.save_definition(
    "conhecimento",
    "Informação compreendida."
)

db.save_definition(
    "aprendizado",
    "Processo de adquirir conhecimento."
)

db.save_definition(
    "memoria",
    "Local onde conhecimentos são armazenados."
)

print(
    "Conhecimentos iniciais carregados."
)