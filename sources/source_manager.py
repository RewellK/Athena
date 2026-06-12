import time

from sources.credential_manager import CredentialManager
from sources.evidence_engine import EvidenceEngine
from sources.external_research_worker import AsyncExternalResearchWorker
from sources.freshness_engine import FreshnessEngine
from sources.source_discovery_engine import SourceDiscoveryEngine
from sources.source_registry import SourceRegistry
from sources.source_trust_engine import SourceTrustEngine
from sources.source_validator import SourceValidator


class SourceManager:
    """Coordinates source discovery, registry, validation and research jobs."""

    DOMAIN_LABELS = {
        "weather": "clima",
        "news": "notícias",
        "vehicles": "veículos",
        "finance": "finanças/cotação",
        "sports": "esportes",
        "places": "lugares",
        "documentation": "documentação",
        "general_web": "web geral",
        "unknown_external": "informação externa",
    }

    def __init__(
        self,
        settings=None,
        registry=None,
        discovery_engine=None,
        evidence_engine=None,
        freshness_engine=None,
        trust_engine=None,
        credential_manager=None,
        validator=None,
        worker=None,
        logger=None,
    ):
        self.settings = settings
        self.logger = logger
        self.discovery_engine = discovery_engine or SourceDiscoveryEngine()
        self.registry = registry or SourceRegistry(path=self._setting("sourceRegistryPath", "logs/source_registry.json"), logger=logger)
        self.freshness_engine = freshness_engine or FreshnessEngine()
        self.trust_engine = trust_engine or SourceTrustEngine()
        self.credential_manager = credential_manager or CredentialManager()
        self.validator = validator or SourceValidator()
        self.evidence_engine = evidence_engine or EvidenceEngine(
            path=self._setting("evidenceStorePath", "logs/evidence_records.jsonl"),
            freshness_engine=self.freshness_engine,
            trust_engine=self.trust_engine,
            logger=logger,
        )
        self.worker = worker or AsyncExternalResearchWorker(
            evidence_engine=self.evidence_engine,
            timeout_seconds=int(self._setting("externalResearchTimeoutSeconds", 15)),
            logger=logger,
        )

    def domain_for(self, text, requested_tool=""):
        return self.discovery_engine.detect_domain(f"{text} {requested_tool}")

    def handle_external_request(self, query, requested_tool=""):
        started_at = time.perf_counter()
        if not self._setting("sourcesEnabled", True) or not self._setting("allowExternalRequests", True):
            return self._result(
                "sources_disabled",
                "unknown_external",
                response="Fontes externas estão desativadas agora. Prefiro não inventar essa informação.",
                started_at=started_at,
            )

        domain = self.domain_for(query, requested_tool=requested_tool)
        enabled_sources = self.registry.find_enabled(domain)
        if not enabled_sources:
            proposal = self.discovery_engine.discover(query, domain=domain)
            return self._result(
                "missing_source",
                domain,
                proposal=proposal.to_dict(),
                response=self.missing_source_response(domain, proposal),
                started_at=started_at,
            )

        source = enabled_sources[0]
        if not self.evidence_engine.can_create_trusted_evidence(source):
            return self._result(
                "source_not_validated",
                domain,
                source=source,
                response=(
                    f"Tenho uma fonte cadastrada para {self.domain_label(domain)}, mas ela ainda não está validada "
                    "para gerar evidência confiável. Prefiro não inventar."
                ),
                started_at=started_at,
            )

        job = self.worker.enqueue(domain, query, source)
        return self._result(
            "job_created",
            domain,
            source=source,
            job=job,
            response=f"Vou pesquisar {self.domain_label(domain)} em uma fonte configurada, já te respondo.",
            started_at=started_at,
        )

    def missing_source_response(self, domain, proposal):
        label = self.domain_label(domain)
        return (
            f"Ainda não possuo uma fonte validada para {label}. "
            f"Não sei consultar {label} ainda porque não tenho uma fonte validada para esse domínio. "
            f"Encontrei uma possível fonte: {proposal.name}. "
            f"Posso adicioná-la como fonte candidata para {label}? "
            "Ela ficará desativada até validação humana e não será usada como evidência por enquanto."
        )

    def add_candidate(self, proposal):
        record = self.registry.add_candidate(proposal)
        validation = self.validator.validate(record)
        if validation.get("status") != record.get("status") or validation.get("validation_status") != record.get("validation_status"):
            record = self.registry.update_status(
                record["source_id"],
                validation.get("status", "pending_validation"),
                validation_status=validation.get("validation_status", "needs_manual_validation"),
            )
        return {
            "source": record,
            "validation": validation,
            "evidence_note": self.evidence_engine.unverified_note(record, query=record.get("domain", "")),
        }

    def reject_candidate(self, proposal):
        record = self.registry.add_candidate(proposal)
        rejected = self.registry.reject(record["source_id"])
        return rejected or record

    def domain_label(self, domain):
        return self.DOMAIN_LABELS.get(domain, "informação externa")

    def _result(self, status, domain, response, started_at, proposal=None, source=None, job=None):
        return {
            "status": status,
            "domain": domain,
            "response": response,
            "proposal": proposal,
            "source": source,
            "job": job,
            "duration_ms": int((time.perf_counter() - started_at) * 1000),
        }

    def _setting(self, key, default=None):
        if self.settings and hasattr(self.settings, "get"):
            return self.settings.get(key, default)
        return default
