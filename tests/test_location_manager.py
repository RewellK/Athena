import tempfile
import unittest
from pathlib import Path

from location.location_manager import LocationManager
from location.location_store import LocationStore
from tests.test_v12_5 import make_athena


class MockWeatherConnector:
    def fetch(self, _query, timeout_seconds=None, request=None, source=None):
        location = request["location"]
        return {
            "source_id": "weather.open_meteo",
            "location_name": location["name"],
            "forecast_date": "2026-06-18",
            "summary": "previsão mockada com céu parcialmente nublado.",
            "temperature_min": 15,
            "temperature_max": 24,
            "precipitation_probability": 20,
            "weather_code": 2,
            "raw": {"mock": True},
            "endpoint": "https://api.open-meteo.com/v1/forecast",
        }


class LocationManagerTests(unittest.TestCase):
    def test_location_can_be_saved_described_and_cleared_with_consent(self):
        manager = LocationManager(store=LocationStore())

        saved = manager.save_from_text("minha localização é São Paulo, SP")
        self.assertEqual(saved["city"], "São Paulo")
        self.assertEqual(saved["state"], "SP")
        self.assertEqual(saved["consent_status"], "granted")
        self.assertEqual(saved["precision"], "city")
        self.assertIn("São Paulo, SP", manager.describe())

        previous = manager.clear()
        self.assertEqual(previous["city"], "São Paulo")
        self.assertIn("Não tenho", manager.describe())

    def test_athena_asks_for_location_when_weather_has_no_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                response = athena.chat("Qual a previsão do clima amanhã?")
                metadata = athena.last_response_metadata

                self.assertEqual(metadata["route"], "external_information")
                self.assertEqual(metadata["source_status"], "missing_location")
                self.assertIn("preciso de uma localização", response)
                self.assertEqual(metadata["llm_calls"], 0)
            finally:
                athena.memory.close()

    def test_athena_saves_reports_and_deletes_location_locally(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                response = athena.chat("minha localização é São Paulo, SP")
                self.assertIn("Salvei sua localização padrão como São Paulo, SP", response)
                self.assertIn("não tem coordenadas", response)

                response = athena.chat("qual localização você tem salva?")
                self.assertIn("São Paulo, SP", response)
                self.assertIn("Consentimento: granted", response)

                response = athena.chat("apague minha localização")
                self.assertIn("Apaguei sua localização", response)
                self.assertIsNone(athena.location_manager.current())
            finally:
                athena.memory.close()

    def test_city_without_coordinates_suggests_geocoding_without_weather_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                athena.chat("use São Paulo, SP como minha localização padrão")
                response = athena.chat("Qual a previsão do clima amanhã?")
                metadata = athena.last_response_metadata

                self.assertEqual(metadata["source_status"], "missing_geocoder")
                self.assertEqual(metadata["module_proposal_title"], "GeocodingConnector")
                self.assertIn("não tenho coordenadas", response)
                self.assertIn("GeocodingConnector", response)
                self.assertNotIn("Vou pesquisar o clima", response)
                self.assertEqual(metadata["llm_calls"], 0)
                self.assertIsNotNone(athena.pending_module_proposal)

                response = athena.chat("Sim")
                self.assertIn("GeocodingConnector", response)
                proposals = athena.source_manager.list_module_proposals()
                self.assertEqual(proposals[0]["title"], "GeocodingConnector")
            finally:
                athena.memory.close()

    def test_location_with_coordinates_allows_weather_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            athena = make_athena(Path(tmp))
            try:
                athena.location_manager.save(
                    city="São Paulo",
                    state="SP",
                    country="Brasil",
                    latitude=-23.5505,
                    longitude=-46.6333,
                    source="manual_test",
                    consent_status="granted",
                )
                athena.source_manager.worker.connectors["weather_open_meteo"] = MockWeatherConnector()

                response = athena.chat("Qual a previsão do clima amanhã?")
                metadata = athena.last_response_metadata

                self.assertEqual(metadata["source_status"], "completed")
                self.assertIn("Segundo a fonte Open-Meteo", response)
                self.assertIn("São Paulo, SP, Brasil", response)
                self.assertTrue(metadata["evidence_id"])
            finally:
                athena.memory.close()


if __name__ == "__main__":
    unittest.main()
