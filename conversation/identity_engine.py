class IdentityEngine:
    """Identity answers come from Self Model / identity data, never extraction."""

    def __init__(self, identity, self_model=None):
        self.identity = identity or {}
        self.self_model = self_model

    def respond(self, user_input=None, operation=None, target=None):
        operation = operation or "describe_self"
        if operation == "creator":
            return f"Fui criada por você, {self.identity.get('creator', 'Rewell')}."
        if operation == "describe_creator":
            return self.describe_creator()
        return (
            f"Eu sou {self.identity.get('name', 'Athena')}, uma entidade digital criada por você para aprender, lembrar, raciocinar e evoluir. "
            "Minha identidade, memória e objetivos pertencem ao Athena Core; LLMs são módulos cognitivos que eu uso."
        )

    def describe_creator(self):
        creator = self.identity.get("creator", "Rewell")
        return f"{creator} é meu criador e a pessoa que está conduzindo minha evolução."
