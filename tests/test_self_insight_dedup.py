import unittest

from learning.self_insight_engine import SelfInsightEngine, SelfInsightStore


class SelfInsightDedupTests(unittest.TestCase):
    def test_duplicate_reflection_events_increment_occurrence_count(self):
        engine = SelfInsightEngine(store=SelfInsightStore())
        event = {
            "event_id": "event-1",
            "issue_type": "weather_missing_location",
            "suspected_module": "sources/source_manager.py",
            "explanation": "A consulta de clima foi reconhecida, mas falta localização configurada.",
            "suggestion": "Pedir localização.",
            "suggested_tests": ["Clima sem localização deve pedir localização."],
            "severity": "medium",
        }
        first = engine.create_from_reflection_event(event)
        second = dict(event)
        second["event_id"] = "event-2"
        saved = engine.create_from_reflection_event(second)

        pending = engine.list_pending()
        self.assertEqual(first["insight_id"], saved["insight_id"])
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["occurrence_count"], 2)
        self.assertIn("event-2", pending[0]["related_event_ids"])

    def test_confirmed_insight_receives_new_occurrence_without_duplicate(self):
        engine = SelfInsightEngine(store=SelfInsightStore())
        first = engine.create_from_capability_gap(
            {"domain": "vehicles", "gap_type": "missing_source"},
            {"title": "VehiclePriceConnector", "proposal_id": "proposal-1"},
        )
        engine.approve(first["insight_id"])
        updated = engine.create_from_capability_gap(
            {"domain": "vehicles", "gap_type": "missing_source"},
            {"title": "VehiclePriceConnector", "proposal_id": "proposal-2"},
        )

        self.assertEqual(updated["insight_id"], first["insight_id"])
        self.assertEqual(updated["status"], "confirmed")
        self.assertEqual(updated["occurrence_count"], 2)
        self.assertEqual(engine.list_pending(), [])

    def test_rejected_insight_does_not_reappear_as_pending_immediately(self):
        engine = SelfInsightEngine(store=SelfInsightStore())
        first = engine.create_from_capability_gap(
            {"domain": "weather", "gap_type": "missing_connector"},
            {"title": "GeocodingConnector", "proposal_id": "geo-1"},
        )
        engine.reject(first["insight_id"])
        updated = engine.create_from_capability_gap(
            {"domain": "weather", "gap_type": "missing_connector"},
            {"title": "GeocodingConnector", "proposal_id": "geo-2"},
        )

        self.assertEqual(updated["insight_id"], first["insight_id"])
        self.assertEqual(updated["status"], "rejected")
        self.assertEqual(updated["occurrence_count"], 2)
        self.assertEqual(engine.list_pending(), [])


if __name__ == "__main__":
    unittest.main()
