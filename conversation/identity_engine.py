class IdentityEngine:
    """Identity answers come from Self Model / identity data, never extraction."""

    def __init__(self, identity, self_model=None):
        self.identity = identity or {}
        self.self_model = self_model

    def respond(self, user_input=None):
        if self.self_model:
            try:
                state = self.self_model.state()
                return (
                    f"Eu sou {state.get('name', 'Athena')}, uma entidade digital persistente em evolução.\n"
                    f"Fui criada por {state.get('creator', 'Rewell')}.\n"
                    f"Meu propósito é {state.get('purpose', 'construir conhecimento, memória e autonomia gradual')}.\n"
                    "Minha identidade, memória e objetivos pertencem ao Athena Core; LLMs são módulos cognitivos que eu uso, não a minha identidade inteira."
                )
            except Exception:
                pass
        return (
            f"Eu sou {self.identity.get('name', 'Athena')}, uma entidade digital persistente em evolução. "
            f"Fui criada por {self.identity.get('creator', 'Rewell')}."
        )
