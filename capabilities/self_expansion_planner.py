class SelfExpansionPlanner:
    """Administrative surface for capability gaps and module proposals."""

    def __init__(self, proposal_engine=None):
        self.proposal_engine = proposal_engine

    def respond(self, operation="module_proposals", identifier=None):
        if operation in {"module_proposals", "pending_module_proposals", "capability_gaps"}:
            return self._list_proposals()
        if operation == "approve_module_proposal":
            return self._approve(identifier)
        if operation == "reject_module_proposal":
            return self._reject(identifier)
        return "Ainda não reconheci esse comando de expansão."

    def _list_proposals(self):
        proposals = self.proposal_engine.list_proposals() if self.proposal_engine else []
        if not proposals:
            return "Ainda não tenho propostas de módulo registradas."
        lines = ["Propostas de módulo/lacunas que conheço:"]
        for item in proposals[:12]:
            lines.append(
                f"- {item.get('proposal_id')} | {item.get('title')} | "
                f"domínio={item.get('domain')} | status={item.get('status')} | risco={', '.join(item.get('risks') or [])}"
            )
        return "\n".join(lines)

    def _approve(self, identifier):
        result = self.proposal_engine.approve(identifier) if self.proposal_engine and identifier else None
        if not result:
            return "Não encontrei essa proposta de módulo para aprovar."
        return f"Proposta aprovada: {result.get('title')}. Isso não implementa código automaticamente; apenas libera revisão humana/Codex futura."

    def _reject(self, identifier):
        result = self.proposal_engine.reject(identifier) if self.proposal_engine and identifier else None
        if not result:
            return "Não encontrei essa proposta de módulo para rejeitar."
        return f"Proposta rejeitada: {result.get('title')}."
