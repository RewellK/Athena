import tempfile
import time
import unittest
from pathlib import Path

from sources.source_discovery_engine import SourceDiscoveryEngine
from sources.external_research_worker import AsyncExternalResearchWorker
from sources.evidence_engine import EvidenceEngine
from sources.source_manager import SourceManager
from sources.source_registry import SourceRegistry
from tests.test_v12_5 import make_athena


class LocalSettings:
    def __init__(self, values=None):
        self.values = {
            "defaultWeatherSource": "weather.open_meteo",
            "externalResearchTimeoutSeconds": 3,
            "externalResearchProcessInline": True,
            "weatherForecastTtlSeconds": 3600,
            "weatherDefaultLocation": {
                "city": "",
                "state": "",
                "country": "",
                "latitude": None,
                "longitude": None,
            },
        }
        self.values.update(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)


class MockWeatherConnector:
    def fetch(self, query, timeout_seconds=None, request=None, source=None):
        return {
            "source_id": "weather.open_meteo",
            "location_name": request["location"]["name"],
            "forecast_date": "2026-06-12",
            "summary": "previsão de chuva fraca, mínima de 16°C e máxima de 25°C.",
            "temperature_min": 16,
            "temperature_max": 25,
            "precipitation_probability": 70,
            "weather_code": 61,
            "raw": {"mock": True},
            "endpoint": "https://api.open-meteo.com/v1/forecast",
        }


class SourceManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = str(Path(self.tmp.name) / "source_registry.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_vehicle_source_generates_candidate_proposal(self):
        manager = SourceManager(registry=SourceRegistry(path=self.registry_path))

        result = manager.handle_external_request("Quanto custa um Civic 2020?")

        self.assertEqual(result["status"], "missing_source")
        self.assertEqual(result["domain"], "vehicles")
        self.assertEqual(result["proposal"]["name"], "iCarros")
        self.assertEqual(result["proposal"]["status"], "candidate")
        self.assertTrue(result["proposal"]["requires_human_approval"])
        self.assertIn("fonte candidata", result["response"])

    def test_source_candidate_is_saved_without_becoming_enabled(self):
        manager = SourceManager(registry=SourceRegistry(path=self.registry_path))
        proposal = SourceDiscoveryEngine().discover("Quanto custa um Civic 2020?", domain="vehicles")

        result = manager.add_candidate(proposal.to_dict())
        source = result["source"]

        self.assertEqual(source["status"], "pending_validation")
        self.assertFalse(source["enabled"])
        self.assertNotEqual(source["validation_status"], "passed")
        self.assertFalse(result["evidence_note"]["can_support_factual_answer"])

    def test_rejected_source_is_not_enabled(self):
        manager = SourceManager(registry=SourceRegistry(path=self.registry_path))
        proposal = SourceDiscoveryEngine().discover("notícias de hoje", domain="news")

        rejected = manager.reject_candidate(proposal.to_dict())

        self.assertEqual(rejected["status"], "rejected")
        self.assertFalse(rejected["enabled"])
        self.assertFalse(manager.registry.has_enabled_source("news"))

    def test_athena_suggests_source_and_waits_for_human_approval(self):
        athena = make_athena(Path(self.tmp.name))
        try:
            started_at = time.perf_counter()
            response = athena.chat("Athena, quanto custa um Civic 2020?")
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)

            metadata = athena.last_response_metadata
            self.assertEqual(metadata["route"], "external_information")
            self.assertEqual(metadata["external_domain"], "vehicles")
            self.assertEqual(metadata["source_status"], "missing_source")
            self.assertIn("Não sei consultar veículos ainda", response)
            self.assertIn("iCarros", response)
            self.assertIsNotNone(athena.pending_source_proposal)
            self.assertLess(elapsed_ms, 500)

            response = athena.chat("sim")
            self.assertEqual(athena.last_response_metadata["route"], "pending_confirmation")
            self.assertIn("fonte candidata", response)
            self.assertIn("desativada", response)
            self.assertIsNone(athena.pending_source_proposal)
            self.assertFalse(athena.source_manager.registry.has_enabled_source("vehicles"))
        finally:
            athena.memory.close()

    def test_athena_does_not_invent_news_without_source(self):
        athena = make_athena(Path(self.tmp.name))
        try:
            response = athena.chat("Quais são as notícias de hoje?")
            metadata = athena.last_response_metadata

            self.assertEqual(metadata["route"], "external_information")
            self.assertEqual(metadata["external_domain"], "news")
            self.assertEqual(metadata["source_status"], "missing_source")
            self.assertEqual(metadata["capability_gap_type"], "missing_source")
            self.assertEqual(metadata["module_proposal_title"], "NewsResearchConnector")
            self.assertIn("Não sei consultar notícias ainda", response)
            self.assertIn("proposta de módulo", response)
            self.assertNotIn("manchete:", response.lower())
            self.assertEqual(metadata["llm_calls"], 0)
        finally:
            athena.memory.close()

    def test_athena_suggests_legal_research_connector_without_inventing_jurisprudence(self):
        athena = make_athena(Path(self.tmp.name))
        try:
            response = athena.chat("Athena, busque jurisprudência recente")
            metadata = athena.last_response_metadata

            self.assertEqual(metadata["route"], "external_information")
            self.assertEqual(metadata["external_domain"], "legal")
            self.assertEqual(metadata["source_status"], "missing_source")
            self.assertEqual(metadata["module_proposal_title"], "LegalResearchConnector")
            self.assertIn("pesquisa jurídica", response)
            self.assertIn("proposta de módulo", response)
            self.assertNotIn("STJ", response)
            self.assertEqual(metadata["llm_calls"], 0)
        finally:
            athena.memory.close()

    def test_weather_source_without_location_asks_for_location(self):
        manager = SourceManager(settings=LocalSettings(), registry=SourceRegistry(path=self.registry_path))

        result = manager.handle_external_request("Qual a previsão do clima amanhã?")

        self.assertEqual(result["status"], "missing_location")
        self.assertEqual(result["domain"], "weather")
        self.assertEqual(result["capability_gap"]["gap_type"], "missing_memory_capability")
        self.assertEqual(result["module_proposal"]["title"], "WeatherContextConnector")
        self.assertIn("localização padrão", result["response"])
        self.assertNotIn("Vou pesquisar", result["response"])

    def test_weather_source_with_location_creates_evidence_inline(self):
        settings = LocalSettings({
            "weatherDefaultLocation": {
                "city": "Embu das Artes",
                "state": "SP",
                "country": "Brasil",
                "latitude": -23.6489,
                "longitude": -46.8522,
            }
        })
        evidence = EvidenceEngine()
        worker = AsyncExternalResearchWorker(
            evidence_engine=evidence,
            connectors={"weather_open_meteo": MockWeatherConnector()},
            timeout_seconds=3,
        )
        manager = SourceManager(settings=settings, registry=SourceRegistry(path=self.registry_path), evidence_engine=evidence, worker=worker)

        result = manager.handle_external_request("Qual a previsão do clima amanhã?")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["domain"], "weather")
        self.assertIn("Vou pesquisar o clima", result["response"])
        self.assertIn("Open-Meteo", result["response"])
        self.assertEqual(result["job"]["status"], "completed")
        self.assertEqual(result["job"]["evidence"]["source_id"], "weather.open_meteo")
        self.assertTrue(result["job"]["evidence"]["evidence_id"])
        self.assertEqual(result["job"]["evidence"]["location"], "Embu das Artes, SP, Brasil")
        self.assertEqual(result["job"]["evidence"]["forecast_date"], "2026-06-12")

    def test_athena_weather_without_location_does_not_call_llm_or_invent(self):
        athena = make_athena(Path(self.tmp.name))
        try:
            response = athena.chat("Qual a previsão do clima amanhã?")
            metadata = athena.last_response_metadata

            self.assertEqual(metadata["route"], "external_information")
            self.assertEqual(metadata["external_domain"], "weather")
            self.assertEqual(metadata["source_status"], "missing_location")
            self.assertEqual(metadata["capability_gap_type"], "missing_memory_capability")
            self.assertEqual(metadata["module_proposal_title"], "WeatherContextConnector")
            self.assertIn("localização padrão", response)
            self.assertNotIn("Vai chover", response)
            self.assertEqual(metadata["llm_calls"], 0)
            self.assertFalse(metadata.get("used_source"))
        finally:
            athena.memory.close()


if __name__ == "__main__":
    unittest.main()
