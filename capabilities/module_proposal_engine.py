import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class ModuleProposal:
    title: str
    domain: str
    reason: str
    gap_type: str = "missing_module"
    required_sources: list = field(default_factory=list)
    required_inputs: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    suggested_tests: list = field(default_factory=list)
    documentation_needed: list = field(default_factory=list)
    acceptance_criteria: list = field(default_factory=list)
    evidence_required: bool = True
    human_approval_required: bool = True
    status: str = "proposed"
    source: str = "capability_gap"
    source_message: str = ""
    related_source_candidate: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self):
        payload = asdict(self)
        payload["status"] = _safe_status(payload.get("status"))
        payload["human_approval_required"] = True
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        return cls(**clean)


class ModuleProposalStore:
    def __init__(self, path=None):
        self.path = path
        self._lock = threading.RLock()
        self._proposals = []
        self._load()

    def save(self, proposal):
        proposal = proposal if isinstance(proposal, ModuleProposal) else ModuleProposal.from_dict(proposal)
        payload = proposal.to_dict()
        with self._lock:
            existing = next((item for item in self._proposals if item.get("title") == payload["title"] and item.get("domain") == payload["domain"]), None)
            if existing and existing.get("status") not in {"rejected", "deprecated"}:
                return dict(existing)
            self._proposals.append(payload)
            self._save()
        return dict(payload)

    def list(self, status=None, domain=None, limit=50):
        with self._lock:
            items = list(self._proposals)
        if status:
            items = [item for item in items if item.get("status") == status]
        if domain:
            items = [item for item in items if item.get("domain") == domain]
        return [dict(item) for item in reversed(items[-int(limit):])]

    def update_status(self, proposal_id, status):
        status = _safe_status(status)
        with self._lock:
            for item in self._proposals:
                if item.get("proposal_id") == proposal_id:
                    item["status"] = status
                    item["human_approval_required"] = status in {"proposed", "pending_human_review"}
                    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
                    self._save()
                    return dict(item)
        return None

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        self._proposals = list(payload.get("proposals", [])) if isinstance(payload, dict) else []

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"proposals": self._proposals}, file, ensure_ascii=False, indent=2)


class ModuleProposalEngine:
    """Creates safe module proposals. It never implements code."""

    def __init__(self, store=None):
        self.store = store or ModuleProposalStore()

    def propose_for_gap(self, gap, source_proposal=None, query=""):
        gap = dict(gap or {})
        source_proposal = dict(source_proposal or {})
        domain = gap.get("domain", "unknown_external")
        spec = self._domain_spec(domain, source_proposal)
        return ModuleProposal(
            title=spec["title"],
            domain=domain,
            reason=gap.get("reason") or spec["reason"],
            gap_type=gap.get("gap_type", "missing_module"),
            required_sources=spec["required_sources"],
            required_inputs=spec["required_inputs"],
            risks=spec["risks"],
            suggested_tests=spec["suggested_tests"],
            documentation_needed=spec["documentation_needed"],
            acceptance_criteria=spec["acceptance_criteria"],
            evidence_required=True,
            human_approval_required=True,
            status="proposed",
            source="capability_gap",
            source_message=str(query or ""),
            related_source_candidate=source_proposal.get("name", ""),
        ).to_dict()

    def register(self, proposal):
        proposal = dict(proposal or {})
        proposal["status"] = "pending_human_review"
        return self.store.save(proposal)

    def list_proposals(self, status=None, domain=None):
        return self.store.list(status=status, domain=domain)

    def approve(self, proposal_id):
        return self.store.update_status(proposal_id, "approved")

    def reject(self, proposal_id):
        return self.store.update_status(proposal_id, "rejected")

    def _domain_spec(self, domain, source_proposal):
        source_name = source_proposal.get("name") or "fonte validada"
        specs = {
            "vehicles": {
                "title": "VehiclePriceConnector",
                "reason": "Usuário pediu preço de veículo, mas não há fonte validada e conector habilitado.",
                "required_sources": [f"{source_name} ou outra fonte com permissão/API validada"],
                "required_inputs": ["modelo", "ano", "versão opcional", "cidade/opcional"],
                "risks": ["scraping indevido", "preços desatualizados", "variação por região", "fonte sem API pública"],
                "suggested_tests": [
                    "Pedido de preço de veículo sem fonte validada deve criar proposta e não inventar preço.",
                    "Fonte candidate/pending_validation não deve gerar EvidenceRecord.",
                ],
                "documentation_needed": ["docs/VEHICLE_PRICE_CONNECTOR.md", "política de fonte e evidência"],
                "acceptance_criteria": ["usa fonte validada", "gera EvidenceRecord", "não usa LLM como preço factual"],
            },
            "news": {
                "title": "NewsResearchConnector",
                "reason": "Usuário pediu notícia atual, mas não há fonte validada.",
                "required_sources": [f"{source_name} ou fonte jornalística/API validada"],
                "required_inputs": ["tópico opcional", "janela temporal", "local opcional"],
                "risks": ["notícia obsoleta", "viés editorial", "fonte sem licença/termos claros"],
                "suggested_tests": ["Notícia sem fonte validada deve sugerir proposta e não inventar manchete."],
                "documentation_needed": ["docs/NEWS_RESEARCH_CONNECTOR.md"],
                "acceptance_criteria": ["fonte validada", "TTL curto", "EvidenceRecord obrigatório"],
            },
            "weather": {
                "title": "WeatherContextConnector",
                "reason": "Consulta de clima precisa de contexto/localização ou conector complementar.",
                "required_sources": [source_name],
                "required_inputs": ["cidade ou latitude/longitude", "data"],
                "risks": ["localização ausente", "previsão vencida"],
                "suggested_tests": ["Clima sem localização deve pedir localização e não criar previsão."],
                "documentation_needed": ["docs/WEATHER_OPEN_METEO_CONNECTOR.md"],
                "acceptance_criteria": ["localização configurada", "evidência com TTL", "fallback sem invenção"],
            },
        }
        return specs.get(domain, {
            "title": f"{_pascal(domain)}ResearchConnector",
            "reason": f"Domínio {domain} precisa de módulo/fonte validada.",
            "required_sources": [source_name],
            "required_inputs": ["consulta", "fonte validada"],
            "risks": ["fonte ausente", "evidência insuficiente", "termos de uso desconhecidos"],
            "suggested_tests": [f"Pedido de {domain} sem módulo validado não deve inventar resposta."],
            "documentation_needed": [f"docs/{_slug(domain).upper()}_RESEARCH_CONNECTOR.md"],
            "acceptance_criteria": ["fonte validada", "EvidenceRecord obrigatório", "aprovação humana"],
        })


def _safe_status(status):
    status = str(status or "proposed").strip().lower()
    allowed = {"proposed", "pending_human_review", "approved", "rejected", "implemented", "deprecated"}
    return status if status in allowed else "proposed"


def _slug(text):
    chars = []
    for char in str(text or "unknown"):
        chars.append(char.lower() if char.isalnum() else "_")
    return "_".join(part for part in "".join(chars).split("_") if part) or "unknown"


def _pascal(text):
    return "".join(part.capitalize() for part in _slug(text).split("_")) or "External"
