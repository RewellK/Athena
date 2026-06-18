import time

from capabilities.capability_gap_engine import CapabilityGapEngine
from capabilities.module_proposal_engine import ModuleProposalEngine, ModuleProposalStore
from sources.connectors.weather_open_meteo import WeatherOpenMeteoConnector
from sources.credential_manager import CredentialManager
from sources.evidence_engine import EvidenceEngine
from sources.external_research_worker import AsyncExternalResearchWorker
from sources.freshness_engine import FreshnessEngine
from sources.source_discovery_engine import SourceDiscoveryEngine
from sources.source_registry import SourceRecord, SourceRegistry
from sources.source_trust_engine import SourceTrustEngine
from sources.source_validator import SourceValidator
from research.research_learning_engine import ResearchLearningEngine
from research.research_strategy_memory import ResearchStrategyMemory


class SourceManager:
    """Coordinates source discovery, registry, validation and research jobs."""

    DOMAIN_LABELS = {
        "weather": "clima",
        "news": "notícias",
        "vehicles": "veículos",
        "finance": "finanças/cotação",
        "legal": "pesquisa jurídica",
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
        research_learning_engine=None,
        capability_gap_engine=None,
        module_proposal_engine=None,
        location_manager=None,
        logger=None,
    ):
        self.settings = settings
        self.logger = logger
        self.discovery_engine = discovery_engine or SourceDiscoveryEngine()
        self.capability_gap_engine = capability_gap_engine or CapabilityGapEngine()
        self.module_proposal_engine = module_proposal_engine or ModuleProposalEngine(
            store=ModuleProposalStore(path=self._setting("moduleProposalStorePath", "logs/module_proposals.json"))
        )
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
            connectors={
                "weather_open_meteo": WeatherOpenMeteoConnector(
                    base_url=self._setting("openMeteoForecastUrl", WeatherOpenMeteoConnector.DEFAULT_BASE_URL)
                )
            },
            timeout_seconds=int(self._setting("externalResearchTimeoutSeconds", 15)),
            logger=logger,
        )
        self.research_learning_engine = research_learning_engine or ResearchLearningEngine(
            memory=ResearchStrategyMemory(path=self._setting("researchStrategyStorePath", "logs/research_strategies.json"))
        )
        self.location_manager = location_manager
        self._bootstrap_configured_sources()

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
            strategy = self._observe_missing_source(domain, proposal)
            gap = self._detect_gap(domain, "missing_source", query, source_proposal=proposal.to_dict())
            module_proposal = self._module_proposal_for_gap(gap, proposal.to_dict(), query)
            return self._result(
                "missing_source",
                domain,
                proposal=proposal.to_dict(),
                capability_gap=gap,
                module_proposal=module_proposal,
                research_strategy=strategy,
                response=self.missing_source_response(domain, proposal),
                started_at=started_at,
            )

        source = enabled_sources[0]
        if not self.evidence_engine.can_create_trusted_evidence(source):
            strategy = self._observe_research_result(domain, source, None, "source_not_validated")
            gap = self._detect_gap(domain, "source_not_validated", query, source=source)
            module_proposal = self._module_proposal_for_gap(gap, {}, query)
            return self._result(
                "source_not_validated",
                domain,
                source=source,
                capability_gap=gap,
                module_proposal=module_proposal,
                research_strategy=strategy,
                response=(
                    f"Tenho uma fonte cadastrada para {self.domain_label(domain)}, mas ela ainda não está validada "
                    "para gerar evidência confiável. Prefiro não inventar."
                ),
                started_at=started_at,
            )

        request = self._external_request(domain, query)
        if domain == "weather" and not request.get("location"):
            strategy = self._observe_research_result(domain, source, None, "missing_input")
            missing_status = "missing_geocoder" if request.get("location_status") == "known_without_coordinates" else "missing_location"
            gap = self._detect_gap(domain, missing_status, query, source=source)
            module_proposal = self._module_proposal_for_gap(gap, {}, query)
            return self._result(
                missing_status,
                domain,
                source=source,
                capability_gap=gap,
                module_proposal=module_proposal,
                research_strategy=strategy,
                response=self._missing_weather_location_response(request, module_proposal),
                started_at=started_at,
            )

        job = self.worker.enqueue(domain, query, source, request=request)
        if self._setting("externalResearchProcessInline", True):
            processed = self.worker.process_pending_once()
            if processed and processed.get("status") == "completed":
                strategy = self._observe_research_result(domain, source, processed, "completed")
                return self._result(
                    "completed",
                    domain,
                    source=source,
                    job=processed,
                    research_strategy=strategy,
                    response=self._format_completed_response(domain, source, processed),
                    started_at=started_at,
                )
            strategy = self._observe_research_result(domain, source, processed, "source_failure")
            gap = self._detect_gap(domain, "source_failure", query, source=source)
            module_proposal = self._module_proposal_for_gap(gap, {}, query)
            return self._result(
                "source_failure",
                domain,
                source=source,
                job=processed,
                capability_gap=gap,
                module_proposal=module_proposal,
                research_strategy=strategy,
                response=(
                    f"Tentei consultar a fonte de {self.domain_label(domain)}, mas a consulta falhou. "
                    "Prefiro não inventar."
                ),
                started_at=started_at,
            )

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
        module_proposal = self.module_proposal_engine.propose_for_gap(
            {"domain": domain, "gap_type": "missing_source", "reason": f"Sem fonte validada para {label}."},
            proposal.to_dict() if hasattr(proposal, "to_dict") else proposal,
        )
        existing = self.module_proposal_engine.find_existing(module_proposal)
        module_title = module_proposal.get("title", "módulo futuro")
        existing_text = ""
        if existing and existing.get("status") in {"proposed", "pending_human_review", "approved"}:
            existing_text = f" Já existe uma proposta registrada para {existing.get('title')} com status {existing.get('status')}."
        return (
            f"Ainda não possuo uma fonte validada para {label}. "
            f"Não sei consultar {label} ainda porque não tenho uma fonte validada para esse domínio. "
            f"Encontrei uma possível fonte: {proposal.name}. "
            f"Também percebi uma lacuna de módulo/conector e posso registrar uma proposta: {module_title}. "
            f"Posso adicionar a fonte candidata e criar essa proposta de módulo para {label}?{existing_text} "
            "Ambas ficarão pendentes de validação humana e não serão usadas como evidência por enquanto."
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

    def list_sources(self, domain=None, status=None):
        return self.registry.list_sources(domain=domain, status=status)

    def register_module_proposal(self, proposal):
        return self.module_proposal_engine.register(proposal)

    def list_module_proposals(self, status=None, domain=None):
        return self.module_proposal_engine.list_proposals(status=status, domain=domain)

    def approve_module_proposal(self, proposal_id):
        return self.module_proposal_engine.approve(proposal_id)

    def reject_module_proposal(self, proposal_id):
        return self.module_proposal_engine.reject(proposal_id)

    def domain_label(self, domain):
        return self.DOMAIN_LABELS.get(domain, "informação externa")

    def _bootstrap_configured_sources(self):
        if self._setting("defaultWeatherSource") != "weather.open_meteo":
            return
        self.registry.upsert(
            SourceRecord(
                source_id="weather.open_meteo",
                domain="weather",
                name="Open-Meteo",
                source_type="api",
                url="https://open-meteo.com/en/docs",
                reason="Fonte de previsão meteorológica via API pública configurada para clima.",
                requires_api_key="no",
                supports_api="yes",
                connector_type="weather_open_meteo",
                trust_level="high",
                freshness_ttl_seconds=int(self._setting("weatherForecastTtlSeconds", 3600)),
                status="enabled",
                enabled=True,
                discovered_by="settings",
                validation_status="passed",
                requires_human_approval=True,
            )
        )

    def _external_request(self, domain, query):
        if domain != "weather":
            return {}
        location = self._weather_location()
        if not location:
            query_location = self._weather_query_location(query)
            if query_location:
                return {
                    "date_mode": self._weather_date_mode(query),
                    "language": "pt-BR",
                    "location_status": "known_without_coordinates",
                    "query_location": query_location,
                    "location_label": self._location_label(query_location),
                }
            return {
                "date_mode": self._weather_date_mode(query),
                "language": "pt-BR",
                "location_status": self._weather_location_status(),
            }
        return {
            "date_mode": self._weather_date_mode(query),
            "language": "pt-BR",
            "location": location,
        }

    def _weather_query_location(self, query):
        manager = getattr(self, "location_manager", None)
        if manager and hasattr(manager, "parse_weather_query_location"):
            location = manager.parse_weather_query_location(query)
            if location and location.get("city"):
                return location
        return {}

    def _weather_location(self):
        manager = getattr(self, "location_manager", None)
        if manager and hasattr(manager, "weather_location"):
            location = manager.weather_location()
            if location:
                return location
        location = self._setting("weatherDefaultLocation", {}) or {}
        try:
            latitude = float(location.get("latitude"))
            longitude = float(location.get("longitude"))
        except (TypeError, ValueError):
            return None
        city = str(location.get("city") or "").strip()
        state = str(location.get("state") or "").strip()
        country = str(location.get("country") or "").strip()
        parts = [part for part in (city, state, country) if part]
        return {
            "city": city,
            "state": state,
            "country": country,
            "latitude": latitude,
            "longitude": longitude,
            "name": ", ".join(parts) or "localização configurada",
        }

    def _weather_location_status(self):
        manager = getattr(self, "location_manager", None)
        if manager and hasattr(manager, "current"):
            location = manager.current()
            if location and location.get("consent_status") == "granted":
                return "known_without_coordinates"
            if location and location.get("consent_status") == "denied":
                return "denied"
        return "missing"

    def _missing_weather_location_response(self, request, module_proposal=None):
        manager = getattr(self, "location_manager", None)
        if request.get("query_location"):
            label = request.get("location_label") or self._location_label(request.get("query_location"))
            response = (
                f"Entendi que você quer o clima para {label}, mas ainda não tenho coordenadas nem geocoder habilitado para essa cidade. "
                "Não vou inventar latitude/longitude. Posso criar uma proposta de módulo GeocodingConnector para transformar cidade em coordenadas com validação humana."
            )
        elif manager and hasattr(manager, "weather_missing_response"):
            response = manager.weather_missing_response()
        else:
            response = (
                "Ainda não possuo uma localização padrão para clima. "
                "Para consultar clima, preciso de uma cidade com latitude/longitude configurada "
                "ou de um geocoder habilitado."
            )
        if request.get("location_status") == "known_without_coordinates" and module_proposal:
            response += f"\nProposta sugerida: {module_proposal.get('title')} ({module_proposal.get('status')})."
        return response

    def _location_label(self, location):
        location = dict(location or {})
        parts = [
            str(location.get("city") or "").strip(),
            str(location.get("state") or "").strip(),
            str(location.get("country") or "").strip(),
        ]
        return ", ".join(part for part in parts if part) or "localização informada"

    def _weather_date_mode(self, query):
        normalized = str(query or "").lower()
        if "amanh" in normalized:
            return "tomorrow"
        return "today"

    def _format_completed_response(self, domain, source, job):
        if domain != "weather":
            return f"Concluí a consulta em {self.domain_label(domain)} com evidência registrada."
        evidence = job.get("evidence") or {}
        result = job.get("result") or {}
        if not evidence:
            return "A fonte de clima retornou dados, mas não consegui registrar evidência. Prefiro não inventar."
        return (
            "Vou pesquisar o clima, já te respondo.\n\n"
            f"Segundo a fonte {source.get('name')} consultada agora, "
            f"em {result.get('location_name', 'localização configurada')} "
            f"para {result.get('forecast_date')}: {result.get('summary')}\n"
            f"Fonte: {source.get('name')}\n"
            f"Evidência: {evidence.get('evidence_id')}\n"
            f"Válido até: {evidence.get('valid_until')}"
        )

    def _observe_missing_source(self, domain, proposal):
        engine = getattr(self, "research_learning_engine", None)
        if not engine:
            return None
        try:
            return engine.observe_missing_source(domain, proposal.to_dict() if hasattr(proposal, "to_dict") else proposal)
        except Exception as error:
            if self.logger:
                self.logger.log("RESEARCH_LEARNING_ERROR", str(error))
            return None

    def _observe_research_result(self, domain, source, job, status):
        engine = getattr(self, "research_learning_engine", None)
        if not engine:
            return None
        try:
            return engine.observe_external_result(domain, source=source, result=job or {}, status=status)
        except Exception as error:
            if self.logger:
                self.logger.log("RESEARCH_LEARNING_ERROR", str(error))
            return None

    def _detect_gap(self, domain, status, query, source_proposal=None, source=None):
        try:
            return self.capability_gap_engine.detect_external_gap(
                domain,
                status,
                query=query,
                source_proposal=source_proposal,
                source=source,
            )
        except Exception as error:
            if self.logger:
                self.logger.log("CAPABILITY_GAP_ERROR", str(error))
            return None

    def _module_proposal_for_gap(self, gap, source_proposal, query):
        if not gap:
            return None
        try:
            proposal = self.module_proposal_engine.propose_for_gap(gap, source_proposal=source_proposal, query=query)
            engine = getattr(self, "research_learning_engine", None)
            if engine and hasattr(engine, "observe_capability_gap"):
                engine.observe_capability_gap(gap.get("domain"), gap=gap, module_proposal=proposal)
            return proposal
        except Exception as error:
            if self.logger:
                self.logger.log("MODULE_PROPOSAL_ERROR", str(error))
            return None

    def _result(
        self,
        status,
        domain,
        response,
        started_at,
        proposal=None,
        source=None,
        job=None,
        research_strategy=None,
        capability_gap=None,
        module_proposal=None,
    ):
        return {
            "status": status,
            "domain": domain,
            "response": response,
            "proposal": proposal,
            "source": source,
            "job": job,
            "research_strategy": research_strategy,
            "capability_gap": capability_gap,
            "module_proposal": module_proposal,
            "duration_ms": int((time.perf_counter() - started_at) * 1000),
        }

    def _setting(self, key, default=None):
        if self.settings and hasattr(self.settings, "get"):
            return self.settings.get(key, default)
        return default
