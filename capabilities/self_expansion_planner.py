class SelfExpansionPlanner:
    """Administrative surface for capability gaps and module proposals."""

    def __init__(self, proposal_engine=None):
        self.proposal_engine = proposal_engine

    def respond(self, operation="module_proposals", identifier=None, user_input=""):
        if operation in {"module_proposals", "pending_module_proposals", "capability_gaps"}:
            return self._list_proposals()
        if operation == "create_module_proposal":
            return self._create_proposal(user_input)
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

    def _create_proposal(self, user_input):
        if not self.proposal_engine:
            return "Ainda não tenho ModuleProposalEngine conectado."
        gap = self._gap_from_text(user_input)
        proposal = self.proposal_engine.propose_for_gap(gap, query=user_input)
        saved = self.proposal_engine.register(proposal)
        if saved.get("deduplicated"):
            return (
                f"Já existia uma proposta para {saved.get('title')}. "
                f"Atualizei a ocorrência para {saved.get('occurrence_count')} e mantive status {saved.get('status')}."
            )
        return (
            f"Criei a proposta de módulo {saved.get('title')} com status {saved.get('status')}. "
            "Ela registra riscos, testes e critérios, mas não implementa código automaticamente."
        )

    def _gap_from_text(self, text):
        normalized = _normalize(text)
        if any(term in normalized for term in ("geocoder", "geocoding", "coordenada", "latitude", "longitude", "localizacao")):
            return {
                "domain": "weather",
                "gap_type": "missing_geocoder",
                "requested_capability": "geocoding",
                "reason": "Usuário solicitou uma melhoria relacionada a localização/geocoding.",
            }
        if any(term in normalized for term in ("painel", "interface", "gui", "workbench visual", "aprendizado")):
            return {
                "domain": "learning_review",
                "gap_type": "missing_gui_interface",
                "reason": "Usuário solicitou uma interface de revisão de aprendizado.",
            }
        if any(term in normalized for term in ("jurisprudencia", "juridico", "juridica", "legal")):
            return {
                "domain": "legal",
                "gap_type": "missing_source",
                "reason": "Usuário solicitou capacidade de pesquisa jurídica validada.",
            }
        return {
            "domain": "unknown_external",
            "gap_type": "missing_module",
            "reason": "Usuário solicitou proposta genérica de melhoria/módulo.",
        }


def _normalize(text):
    normalized = str(text or "").lower()
    for source, target in {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }.items():
        normalized = normalized.replace(source, target)
    return " ".join(normalized.split())
