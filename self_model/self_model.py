import json


class SelfModel:
    """Athena's model of herself, generated from internal state."""

    def __init__(self, memory, identity, settings, llm_provider=None, context_builder=None):
        self.memory = memory
        self.identity = identity
        self.settings = settings
        self.llm_provider = llm_provider
        self.context_builder = context_builder

    def respond(self, user_input):
        state = self.state()
        if self.llm_provider:
            prompt = f"""
Você é o Self Model da Athena.
Responda sobre o estado interno da Athena com base somente nestes dados.
Não invente capacidades.
Se uma limitação existir, declare com honestidade.

Pergunta:
{user_input}

Estado interno:
{json.dumps(state, ensure_ascii=False, indent=2)}
""".strip()
            result = self.llm_provider.generate(prompt)
            if result.available and result.text:
                return result.text.strip()
        return self._fallback(state)

    def answer(self, user_input):
        return self.respond(user_input)

    def state(self):
        return {
            "name": self.identity.get("name"),
            "creator": self.identity.get("creator"),
            "purpose": self.identity.get("purpose"),
            "llm": {
                "enabled": self.settings.get("useLLM", True),
                "model": self.settings.get("ollamaModel"),
                "url": self.settings.get("ollamaUrl"),
            },
            "voice": {
                "enabled": self.settings.get("voiceEnabled", False),
                "provider": self.settings.get("voiceProvider"),
                "fallback": self.settings.get("fallbackVoiceProvider"),
            },
            "counts": {
                "memories": self.memory.count_memories(),
                "short_term": self.memory.count_short_term_memory(),
                "mid_term": self.memory.count_mid_term_memory(),
                "long_term": self.memory.count_real_long_term_memory(),
                "relationships": self.memory.count_world_relationships(),
                "goals": len(self.memory.list_goals()),
                "events": self.memory.count_world_events(),
                "entities": self.memory.count_entities(),
                "states": self.memory.count_entity_states(),
                "intentions": len(self.memory.list_intentions(limit=100000)),
                "agency_goals": len(self.memory.list_agency_goals(limit=100000)),
                "plans": len(self.memory.list_plans(limit=100000)),
                "actions": len(self.memory.list_actions(limit=100000)),
                "outcomes": len(self.memory.list_outcomes(limit=100000)),
                "knowledge_sources": self.memory.count_knowledge_sources(),
                "beliefs": self.memory.count_reasoning_conclusions("belief"),
                "hypotheses": self.memory.count_reasoning_conclusions("hypothesis"),
            },
            "current_limitations": [
                "não tenho percepção contínua fora das interações",
                "não executo ações permanentes sem aprovação humana",
                "não devo transformar hipótese em fato",
                "quando a LLM local falha, peço contexto em vez de adivinhar",
            ],
        }

    def _fallback(self, state):
        counts = state["counts"]
        return (
            "Estou funcional.\n"
            f"Tenho {counts['memories']} memórias, {counts['entities']} entidades, "
            f"{counts['relationships']} relações, {counts['agency_goals']} objetivos de agência e "
            f"{counts['actions']} ações registradas.\n"
            f"Uso o modelo local configurado: {state['llm']['model']}.\n"
            "Minha principal limitação atual é não possuir percepção contínua fora das conversas."
        )
