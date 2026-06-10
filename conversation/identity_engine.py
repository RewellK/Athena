class IdentityEngine:
    """Identity answers come from Self Model / identity data, never extraction."""

    def __init__(self, identity, self_model=None):
        self.identity = identity or {}
        self.self_model = self_model

    def respond(self, user_input=None, operation=None, target=None, intent=None):
        operation = operation or intent or "self_identity"
        if operation in {"creator", "creator_query"}:
            return f"Fui criada por você, {self.identity.get('creator', 'Rewell')}."
        if operation in {"describe_creator", "user_identity"}:
            return self.describe_creator()
        return (
            f"Eu sou {self.identity.get('name', 'Athena')}, uma entidade digital criada por você para aprender, lembrar, raciocinar e evoluir. "
            "Minha identidade, memória e objetivos pertencem ao Athena Core; LLMs são módulos cognitivos que eu uso para interpretar linguagem e refletir."
        )

    def describe_creator(self):
        creator = self.identity.get("creator", "Rewell")
        return f"{creator} é meu criador e a pessoa que está conduzindo minha evolução."
