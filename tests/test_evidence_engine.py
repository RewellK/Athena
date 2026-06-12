import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from sources.evidence_engine import EvidenceEngine
from sources.freshness_engine import FreshnessEngine
from sources.source_registry import SourceProposal, SourceRegistry


class EvidenceEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.evidence = EvidenceEngine(path=str(Path(self.tmp.name) / "evidence.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_candidate_source_cannot_generate_trusted_evidence(self):
        registry = SourceRegistry()
        source = registry.add_candidate(SourceProposal(domain="vehicles", name="iCarros"))

        with self.assertRaises(ValueError):
            self.evidence.create_record(source, "Civic 2020", {"price": "unknown"})

        note = self.evidence.unverified_note(source, "Civic 2020")
        self.assertEqual(note["note_type"], "unverified_source_note")
        self.assertFalse(note["can_support_factual_answer"])

    def test_enabled_validated_source_generates_evidence_record(self):
        source = {
            "source_id": "weather.mock",
            "domain": "weather",
            "name": "Weather Mock",
            "status": "enabled",
            "enabled": True,
            "validation_status": "passed",
            "trust_level": "medium",
            "freshness_ttl_seconds": 1800,
            "url": "https://example.invalid/weather",
        }

        record = self.evidence.create_record(source, "previsão do clima", {"summary": "mock"})

        self.assertEqual(record["source_id"], "weather.mock")
        self.assertEqual(record["domain"], "weather")
        self.assertIn("fetched_at", record)
        self.assertIn("valid_until", record)
        self.assertTrue(self.evidence.freshness_engine.is_fresh(record))

    def test_freshness_engine_marks_expired_evidence(self):
        freshness = FreshnessEngine()
        expired = {
            "valid_until": (datetime.now() - timedelta(seconds=1)).isoformat(timespec="seconds")
        }

        self.assertFalse(freshness.is_fresh(expired))


if __name__ == "__main__":
    unittest.main()
