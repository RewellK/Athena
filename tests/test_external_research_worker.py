import time
import unittest

from sources.evidence_engine import EvidenceEngine
from sources.external_research_worker import AsyncExternalResearchWorker


class MockWeatherConnector:
    def fetch(self, query, timeout_seconds=None):
        return {"query": query, "summary": "tempo mockado", "temperature_c": 22}


class ExternalResearchWorkerTests(unittest.TestCase):
    def test_worker_enqueues_quickly_and_processes_with_mock_connector(self):
        source = {
            "source_id": "weather.mock",
            "domain": "weather",
            "name": "Weather Mock",
            "status": "enabled",
            "enabled": True,
            "validation_status": "passed",
            "trust_level": "medium",
            "freshness_ttl_seconds": 1800,
            "connector_type": "weather_mock",
            "url": "https://example.invalid/weather",
        }
        worker = AsyncExternalResearchWorker(
            evidence_engine=EvidenceEngine(),
            connectors={"weather_mock": MockWeatherConnector()},
            timeout_seconds=2,
        )

        started_at = time.perf_counter()
        job = worker.enqueue("weather", "previsão do clima amanhã", source)
        enqueue_ms = int((time.perf_counter() - started_at) * 1000)

        self.assertEqual(job["status"], "pending")
        self.assertLess(enqueue_ms, 100)
        self.assertEqual(worker.pending_count(), 1)

        processed = worker.process_pending_once()

        self.assertEqual(processed["status"], "completed")
        self.assertEqual(processed["result"]["summary"], "tempo mockado")
        self.assertEqual(processed["evidence"]["source_id"], "weather.mock")
        self.assertEqual(worker.pending_count(), 0)

    def test_worker_failure_does_not_invent_result(self):
        source = {
            "source_id": "weather.no_connector",
            "domain": "weather",
            "name": "No Connector",
            "status": "enabled",
            "enabled": True,
            "validation_status": "passed",
            "trust_level": "medium",
            "connector_type": "missing",
        }
        worker = AsyncExternalResearchWorker(evidence_engine=EvidenceEngine(), connectors={})
        worker.enqueue("weather", "previsão", source)

        processed = worker.process_pending_once()

        self.assertEqual(processed["status"], "failed")
        self.assertIn("Nenhum conector", processed["error"])
        self.assertEqual(processed["result"], {})


if __name__ == "__main__":
    unittest.main()
