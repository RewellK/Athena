import json


class CuriosityEngine:
    """Curiosity from recurrence, importance and relational density, not fixed topics."""

    def __init__(self, memory, memory_manager, creator_name="Rewell", llm_provider=None, context_builder=None):
        self.memory = memory
        self.memory_manager = memory_manager
        self.creator_name = creator_name
        self.llm_provider = llm_provider
        self.context_builder = context_builder

    def respond(self, user_input):
        question = self.generate_question(user_input)
        if question:
            return question
        return "Ainda não tenho padrões suficientes para formular uma curiosidade segura."

    def answer(self, user_input):
        return self.respond(user_input)

    def generate_question(self, user_input=""):
        observations = self._observations()
        if not observations:
            return None
        if self.llm_provider:
            prompt = f"""
Você é o Curiosity Engine da Athena.
Gere uma pergunta útil baseada apenas nas observações estruturadas.
Não use tópicos fixos, nomes especiais ou regras por domínio.
A pergunta deve pedir autorização ou esclarecimento, não executar ação.

Mensagem atual:
{user_input}

Observações:
{json.dumps(observations, ensure_ascii=False, indent=2)}
""".strip()
            result = self.llm_provider.generate(prompt)
            if result.available and result.text:
                return result.text.strip()
        first = observations[0]
        return f"Percebi um padrão recorrente: {first.get('summary', first.get('statement', 'algo apareceu mais de uma vez'))}. Quer me dar mais contexto sobre isso?"

    def _observations(self):
        items = []
        for row in self.memory.list_mid_term_memory(include_expired=False)[:20]:
            _id, summary, topics, source_count, created_at, expires_at, importance_score, promoted = row
            items.append({
                "kind": "mid_term_pattern",
                "summary": summary,
                "topics": topics,
                "source_count": source_count,
                "importance_score": importance_score,
            })
        for row in self.memory.list_reasoning_conclusions("hypothesis")[:10]:
            _id, category, statement, confidence, evidence_json, origin, created_at = row
            items.append({
                "kind": "hypothesis",
                "statement": statement,
                "confidence": confidence,
                "origin": origin,
            })
        return items
