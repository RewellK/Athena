from memory.database import MemoryDB


INITIAL_DEFINITIONS = [
    (
        "athena",
        "Meu nome. Sou uma entidade digital persistente criada por Rewell."
    ),
    (
        "rewell",
        "Meu criador."
    ),
    (
        "conhecimento",
        "Informação compreendida e organizada."
    ),
    (
        "aprendizado",
        "Processo de adquirir e preservar conhecimento ao longo do tempo."
    ),
    (
        "memoria",
        "Local persistente onde conhecimentos, conversas e relações são armazenados."
    ),
]

INITIAL_RELATIONSHIPS = [
    ("Athena", "creator", "Rewell"),
]


class AthenaBootstrap:

    def __init__(self, memory=None):
        self.memory = memory or MemoryDB()

    def run(self):
        self.memory.create_tables()
        self.seed_definitions()
        self.seed_relationships()
        self.seed_world_model()

    def seed_definitions(self):
        for concept, meaning in INITIAL_DEFINITIONS:
            if not self.memory.get_definition(concept):
                self.memory.save_definition(concept, meaning)

    def seed_relationships(self):
        for source, relation, target in INITIAL_RELATIONSHIPS:
            existing = self.memory.find_relationships(
                source=source,
                relation=relation,
                target=target
            )

            if not existing:
                self.memory.save_relationship(source, relation, target)

    def seed_world_model(self):
        self.memory.save_entity("Athena", "project")
        self.memory.save_entity("Rewell", "person")
        self.memory.save_world_relationship("Athena", "criada_por", "Rewell", confidence=100)


def bootstrap():
    AthenaBootstrap().run()
