import json
from datetime import datetime, timedelta


class ReflectionEngine:
    """
    V11 reflection is evidence-driven.
    It does not map user phrases to fixed behaviours. The Orchestrator routes
    reflection requests through structured intention.
    """

    def __init__(self, memory, identity, context_builder=None, llm_provider=None):
        self.memory = memory
        self.identity = identity
        self.context_builder = context_builder
        self.llm_provider = llm_provider

    def respond(self, user_input):
        evidence = self._reflection_evidence()
        if self.llm_provider:
            prompt = f"""
Você é o Reflection Engine da Athena.
Responda com base somente nas evidências do Athena Core.
Não invente fatos.
Diferencie conhecimento, crença e hipótese.
Se faltar dado, diga que ainda não sabe.

Pergunta do usuário:
{user_input}

Evidências:
{json.dumps(evidence, ensure_ascii=False, indent=2)}
""".strip()
            result = self.llm_provider.generate(prompt)
            if result.available and result.text:
                return result.text.strip()
        return self._fallback_summary(evidence)

    def opinion(self, user_input):
        return self.respond(user_input)

    def _reflection_evidence(self):
        today = datetime.now().date().isoformat()
        week_start = (datetime.now() - timedelta(days=7)).date().isoformat()
        today_memories = self.memory.list_memories(created_at_prefix=today)
        week_ingestions = self.memory.list_knowledge_ingestions(created_at_prefix=week_start)
        return {
            "identity": self.identity,
            "counts": {
                "memories": self.memory.count_memories(),
                "short_term_memory": self.memory.count_short_term_memory(),
                "mid_term_memory": self.memory.count_mid_term_memory(),
                "long_term_memory": self.memory.count_real_long_term_memory(),
                "entities": self.memory.count_entities(),
                "relationships": self.memory.count_world_relationships(),
                "events": self.memory.count_world_events(),
                "states": self.memory.count_entity_states(),
                "knowledge_sources": self.memory.count_knowledge_sources(),
                "beliefs": self.memory.count_reasoning_conclusions("belief"),
                "hypotheses": self.memory.count_reasoning_conclusions("hypothesis"),
            },
            "today_memories": today_memories[:20],
            "mid_term_patterns": self.memory.list_mid_term_memory(include_expired=False)[:20],
            "recent_knowledge_sources": self.memory.list_knowledge_sources()[:10],
            "recent_ingestions_reference_date": week_start,
            "recent_ingestions": week_ingestions[:10],
            "recent_conclusions": self.memory.list_reasoning_conclusions()[:20],
            "recent_outcomes": self.memory.list_outcomes(limit=10),
        }

    def _fallback_summary(self, evidence):
        counts = evidence["counts"]
        return (
            "Consigo refletir parcialmente usando minha memória interna.\n"
            f"Memórias: {counts['memories']} | Entidades: {counts['entities']} | Relações: {counts['relationships']} | "
            f"Crenças: {counts['beliefs']} | Hipóteses: {counts['hypotheses']}.\n"
            "Minha LLM local não está disponível para uma reflexão mais profunda agora."
        )
