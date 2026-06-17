from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class CapabilityGap:
    gap_type: str
    domain: str
    reason: str
    requested_capability: str = ""
    missing_inputs: list = field(default_factory=list)
    source_status: str = ""
    source_candidate: str = ""
    requires_human_review: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)


class CapabilityGapEngine:
    """Detects missing organs/capabilities without inventing them."""

    def detect_external_gap(self, domain, status, query="", source_proposal=None, source=None):
        source_proposal = dict(source_proposal or {})
        source = dict(source or {})
        domain = str(domain or "unknown_external")
        status = str(status or "")
        if status == "missing_source":
            return CapabilityGap(
                gap_type="missing_source",
                domain=domain,
                requested_capability=self._capability_name(domain),
                source_status=status,
                source_candidate=source_proposal.get("name", ""),
                reason=f"Pedido externo em {domain} sem fonte validada/enabled.",
            ).to_dict()
        if status == "source_not_validated":
            return CapabilityGap(
                gap_type="missing_validation_flow",
                domain=domain,
                requested_capability=self._capability_name(domain),
                source_status=status,
                source_candidate=source.get("name", ""),
                reason=f"Fonte existente para {domain} ainda não passou por validação.",
            ).to_dict()
        if status == "missing_location":
            return CapabilityGap(
                gap_type="missing_memory_capability",
                domain=domain,
                requested_capability="weather_location_context",
                missing_inputs=["location"],
                source_status=status,
                source_candidate=source.get("name", ""),
                reason="Consulta de clima precisa de localização ou geocoder configurado.",
            ).to_dict()
        if status == "missing_geocoder":
            return CapabilityGap(
                gap_type="missing_connector",
                domain=domain,
                requested_capability="geocoding",
                missing_inputs=["latitude", "longitude"],
                source_status=status,
                source_candidate=source.get("name", ""),
                reason="Existe cidade salva, mas falta um geocoder validado para obter latitude/longitude.",
            ).to_dict()
        if status == "source_failure":
            return CapabilityGap(
                gap_type="missing_resilience",
                domain=domain,
                requested_capability=self._capability_name(domain),
                source_status=status,
                source_candidate=source.get("name", ""),
                reason=f"Conector/fonte para {domain} falhou durante consulta.",
            ).to_dict()
        return None

    def _capability_name(self, domain):
        return {
            "vehicles": "vehicle_price_research",
            "news": "news_research",
            "weather": "weather_research",
            "finance": "finance_quote_research",
            "legal": "legal_research",
        }.get(domain, f"{domain}_research")
