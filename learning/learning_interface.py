class LearningInterface:
    """Local training/admin interface for Athena's learnable organs."""

    def __init__(self, workbench=None, self_insight_engine=None, teacher_loop=None):
        self.workbench = workbench
        self.self_insight_engine = self_insight_engine
        self.teacher_loop = teacher_loop

    def respond(self, operation, identifier=None, user_input=""):
        if operation == "pending_training_examples":
            return self._pending_examples()
        if operation == "learned_linguistic_patterns":
            return self._patterns()
        if operation == "local_patterns_without_llm":
            return self._local_patterns_without_llm()
        if operation == "llm_dependencies":
            return self._llm_dependencies()
        if operation == "create_training_example_from_correction":
            return self._create_training_example_from_correction(user_input)
        if operation == "pending_self_insights":
            return self._pending_insights()
        if operation == "llm_teacher_insights":
            return self._teacher_insights()
        if operation == "approve_training_example":
            return self._approve_example(identifier)
        if operation == "reject_training_example":
            return self._reject_example(identifier)
        if operation == "approve_self_insight":
            return self._approve_insight(identifier)
        if operation == "reject_self_insight":
            return self._reject_insight(identifier)
        return "Ainda não reconheci esse comando de aprendizagem."

    def _create_training_example_from_correction(self, user_input):
        if not self.workbench:
            return "Ainda não tenho LearningWorkbench disponível para registrar correções."
        phrase = self._quoted_phrase(user_input) or str(user_input or "").strip()
        normalized = phrase.lower()
        expected_intent = "entity_query" if any(token in normalized.split() for token in {"ela", "ele", "dela", "dele"}) else "unknown"
        example = self.workbench.save_example({
            "utterance": phrase,
            "expected_intent": expected_intent,
            "expected_object": phrase,
            "expected_scope": "all_known_facts" if expected_intent == "entity_query" else "",
            "source": "human_feedback",
            "confidence": 0.8,
            "status": "pending_human_review",
            "requires_human_review": True,
            "correction": str(user_input or "").strip(),
        })
        return (
            f"Registrei um exemplo de treino pendente: {example.get('id')}. "
            "Ele ainda não virou padrão local; precisa de aprovação humana."
        )

    def _pending_examples(self):
        examples = self.workbench.list_examples(status="candidate") if self.workbench else []
        examples += self.workbench.list_examples(status="pending_human_review") if self.workbench else []
        if not examples:
            return "Ainda não tenho exemplos de treino pendentes."
        lines = ["Exemplos de treino pendentes:"]
        for item in examples[:10]:
            lines.append(f"- {item.get('id')} | {item.get('expected_intent')} | {item.get('utterance')}")
        return "\n".join(lines)

    def _patterns(self):
        patterns = self.workbench.list_patterns(status="confirmed") if self.workbench else []
        if not patterns:
            return "Ainda não tenho padrões linguísticos confirmados."
        lines = ["Padrões linguísticos aprendidos:"]
        for item in patterns[:10]:
            lines.append(f"- {item.get('id')} | {item.get('name')} | intent={item.get('intent')} | match={item.get('match_text')}")
        return "\n".join(lines)

    def _local_patterns_without_llm(self):
        patterns = self.workbench.list_patterns(status="confirmed") if self.workbench else []
        if not patterns:
            return "Ainda não tenho padrões confirmados para reutilizar sem LLM nesse ponto."
        lines = ["Consigo reutilizar estes padrões locais sem LLM:"]
        for item in patterns[:10]:
            lines.append(f"- {item.get('name')} | intent={item.get('intent')} | match={item.get('match_text')}")
        return "\n".join(lines)

    def _llm_dependencies(self):
        pending = self.workbench.list_examples(status="candidate") if self.workbench else []
        pending += self.workbench.list_examples(status="pending_human_review") if self.workbench else []
        if not pending:
            return "Neste órgão de aprendizado, não tenho exemplos pendentes que dependam da LLM agora."
        return (
            f"Ainda tenho {len(pending)} exemplo(s) candidato(s) que precisam de validação antes de virarem padrão local. "
            "Até isso acontecer, eu posso precisar de LLM em casos parecidos."
        )

    def _pending_insights(self):
        insights = self.self_insight_engine.list_pending(limit=10) if self.self_insight_engine else []
        if not insights:
            return "Ainda não tenho insights pendentes sobre mim mesma."
        lines = ["Insights pendentes sobre mim:"]
        for item in insights:
            lines.append(f"- {item.get('insight_id')} | {item.get('insight_type')} | {item.get('content')[:120]}")
        return "\n".join(lines)

    def _teacher_insights(self):
        insights = self.teacher_loop.store.list(status="candidate", limit=10) if self.teacher_loop else []
        if not insights:
            return "A professora LLM ainda não registrou insights candidatos."
        lines = ["Insights candidatos da professora LLM:"]
        for item in insights:
            lines.append(f"- {item.get('insight_id')} | confiança={item.get('confidence')} | {item.get('summary')[:120]}")
        return "\n".join(lines)

    def _approve_example(self, identifier):
        result = self.workbench.validate_example_as_pattern(identifier) if self.workbench and identifier else None
        if not result:
            return "Não encontrei esse exemplo de treino para aprovar."
        return f"Exemplo aprovado e convertido em padrão local: {result.get('name')}."

    def _reject_example(self, identifier):
        result = self.workbench.reject_example(identifier, reason="rejeitado por comando humano") if self.workbench and identifier else None
        if not result:
            return "Não encontrei esse exemplo de treino para rejeitar."
        return "Exemplo de treino rejeitado. Ele não será usado como padrão local."

    def _approve_insight(self, identifier):
        result = self.self_insight_engine.approve(identifier) if self.self_insight_engine and identifier else None
        if not result:
            return "Não encontrei esse insight para aprovar."
        return "Insight aprovado como aprendizado supervisionado."

    def _reject_insight(self, identifier):
        result = self.self_insight_engine.reject(identifier) if self.self_insight_engine and identifier else None
        if not result:
            return "Não encontrei esse insight para rejeitar."
        return "Insight rejeitado. Ele continuará fora dos aprendizados confirmados."

    def _quoted_phrase(self, text):
        raw = str(text or "")
        pairs = [("“", "”"), ('"', '"'), ("'", "'")]
        for start, end in pairs:
            first = raw.find(start)
            if first < 0:
                continue
            second = raw.find(end, first + 1)
            if second > first:
                return raw[first + 1:second].strip()
        return ""
