import unittest

from sources.connectors.weather_open_meteo import WeatherOpenMeteoConnector


class MockHttpClient:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.urls = []
        self.timeouts = []

    def get_json(self, url, timeout_seconds=15):
        self.urls.append(url)
        self.timeouts.append(timeout_seconds)
        if self.error:
            raise self.error
        return self.payload


def valid_payload():
    return {
        "timezone": "America/Sao_Paulo",
        "utc_offset_seconds": -10800,
        "generationtime_ms": 1.2,
        "daily": {
            "time": ["2026-06-11", "2026-06-12"],
            "weather_code": [2, 61],
            "temperature_2m_max": [23.0, 25.5],
            "temperature_2m_min": [14.5, 16.0],
            "precipitation_probability_max": [20, 70],
        },
    }


class WeatherOpenMeteoConnectorTests(unittest.TestCase):
    def test_normalizes_valid_daily_forecast(self):
        client = MockHttpClient(payload=valid_payload())
        connector = WeatherOpenMeteoConnector(http_client=client)

        result = connector.fetch(
            "qual a previsão do clima amanhã?",
            timeout_seconds=3,
            request={
                "date_mode": "tomorrow",
                "location": {
                    "name": "Embu das Artes, SP, Brasil",
                    "latitude": -23.6489,
                    "longitude": -46.8522,
                },
            },
        )

        self.assertEqual(result["source_id"], "weather.open_meteo")
        self.assertEqual(result["location_name"], "Embu das Artes, SP, Brasil")
        self.assertEqual(result["forecast_date"], "2026-06-12")
        self.assertEqual(result["temperature_min"], 16.0)
        self.assertEqual(result["temperature_max"], 25.5)
        self.assertEqual(result["precipitation_probability"], 70)
        self.assertEqual(result["weather_code"], 61)
        self.assertIn("chuva fraca", result["summary"])
        self.assertIn("latitude=-23.6489", client.urls[0])
        self.assertIn("daily=weather_code%2Ctemperature_2m_max", client.urls[0])
        self.assertEqual(client.timeouts[0], 3)

    def test_handles_unknown_weather_code_conservatively(self):
        payload = valid_payload()
        payload["daily"]["weather_code"][1] = 777
        connector = WeatherOpenMeteoConnector(http_client=MockHttpClient(payload=payload))

        result = connector.fetch(
            "clima amanhã",
            request={"date_mode": "tomorrow", "location": {"latitude": 1, "longitude": 2}},
        )

        self.assertIn("código climático 777", result["summary"])

    def test_partial_payload_does_not_invent_missing_values(self):
        payload = {
            "daily": {
                "time": ["2026-06-11", "2026-06-12"],
                "weather_code": [0, 3],
            }
        }
        connector = WeatherOpenMeteoConnector(http_client=MockHttpClient(payload=payload))

        result = connector.fetch(
            "clima amanhã",
            request={"date_mode": "tomorrow", "location": {"latitude": 1, "longitude": 2}},
        )

        self.assertEqual(result["weather_code"], 3)
        self.assertIsNone(result["temperature_min"])
        self.assertIsNone(result["temperature_max"])
        self.assertIn("nublado", result["summary"])

    def test_http_error_and_timeout_are_not_swallowed_as_weather(self):
        for error in [RuntimeError("HTTP 500"), TimeoutError("timeout")]:
            with self.subTest(error=type(error).__name__):
                connector = WeatherOpenMeteoConnector(http_client=MockHttpClient(error=error))
                with self.assertRaises(type(error)):
                    connector.fetch(
                        "clima amanhã",
                        request={"date_mode": "tomorrow", "location": {"latitude": 1, "longitude": 2}},
                    )

    def test_missing_location_fails_before_http(self):
        client = MockHttpClient(payload=valid_payload())
        connector = WeatherOpenMeteoConnector(http_client=client)

        with self.assertRaises(ValueError):
            connector.fetch("clima amanhã", request={"location": {}})
        self.assertEqual(client.urls, [])


if __name__ == "__main__":
    unittest.main()
