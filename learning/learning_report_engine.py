class LearningReportEngine:
    def __init__(self, candidate_store=None):
        self.candidate_store = candidate_store

    def render(self, title="Relatório de aprendizagem", session_id=None, include_all=False):
        if not self.candidate_store:
            return "Ainda não tenho LearningCandidateStore conectado."
        statuses = None if include_all else {"candidate", "edited", "approved", "rejected"}
        candidates = self.candidate_store.list(status=statuses, session_id=session_id, limit=50)
        if not candidates:
            return "Ainda não separei candidatos de aprendizado para revisar."
        lines = [title, f"Separei {len(candidates)} candidato(s). Nada foi consolidado automaticamente."]
        for index, item in enumerate(candidates, start=1):
            lines.extend(
                [
                    "",
                    f"{index}. {self._label(item.get('candidate_type'))}",
                    f"Conteúdo: {item.get('content')}",
                    f"Motivo: {item.get('reason')}",
                    f"Destino sugerido: {item.get('suggested_destination')}",
                    f"Risco: {item.get('risk_level')}",
                    f"Status: {item.get('status')}",
                ]
            )
        lines.append("")
        lines.append("Você pode aprovar, rejeitar, editar ou consolidar os aprovados.")
        return "\n".join(lines)

    def _label(self, candidate_type):
        labels = {
            "memory_candidate": "Possível memória",
            "project_principle": "Princípio de projeto",
            "user_preference": "Preferência do usuário",
            "architecture_rule": "Regra de arquitetura",
            "semantic_pattern": "Padrão semântico",
            "training_example": "Exemplo de treino",
            "self_insight": "SelfInsight",
            "module_proposal": "Proposta de órgão",
            "research_strategy": "Estratégia de pesquisa",
            "memory_policy": "Política de memória",
            "safety_boundary": "Limite de segurança",
            "command_pattern": "Padrão de comando",
        }
        return labels.get(candidate_type, candidate_type or "Candidato")
