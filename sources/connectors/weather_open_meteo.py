import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass
class WeatherResult:
    source_id: str
    location_name: str
    latitude: float
    longitude: float
    forecast_date: str
    summary: str
    temperature_min: float = None
    temperature_max: float = None
    precipitation_probability: float = None
    weather_code: int = None
    raw: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class UrllibJsonHttpClient:
    def get_json(self, url, timeout_seconds=15):
        try:
            with urlopen(url, timeout=timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if status >= 400:
                    raise RuntimeError(f"Open-Meteo retornou HTTP {status}.")
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RuntimeError(f"Open-Meteo retornou HTTP {error.code}.") from error
        except URLError as error:
            raise RuntimeError(f"Falha de rede ao consultar Open-Meteo: {error.reason}") from error
        except TimeoutError as error:
            raise TimeoutError("Tempo limite ao consultar Open-Meteo.") from error


class WeatherOpenMeteoConnector:
    """Connector for Open-Meteo forecast API.

    Contract verified against Open-Meteo docs:
    /v1/forecast accepts latitude/longitude and daily variables. Daily
    variables require timezone.
    """

    DEFAULT_BASE_URL = "https://api.open-meteo.com/v1/forecast"

    WEATHER_CODE_PT_BR = {
        0: "céu limpo",
        1: "principalmente limpo",
        2: "parcialmente nublado",
        3: "nublado",
        45: "neblina",
        48: "neblina com geada",
        51: "garoa fraca",
        53: "garoa moderada",
        55: "garoa intensa",
        56: "garoa congelante fraca",
        57: "garoa congelante intensa",
        61: "chuva fraca",
        63: "chuva moderada",
        65: "chuva forte",
        66: "chuva congelante fraca",
        67: "chuva congelante forte",
        71: "neve fraca",
        73: "neve moderada",
        75: "neve forte",
        77: "grãos de neve",
        80: "pancadas de chuva fracas",
        81: "pancadas de chuva moderadas",
        82: "pancadas de chuva fortes",
        85: "pancadas de neve fracas",
        86: "pancadas de neve fortes",
        95: "tempestade",
        96: "tempestade com granizo fraco",
        99: "tempestade com granizo forte",
    }

    def __init__(self, http_client=None, base_url=None):
        self.http_client = http_client or UrllibJsonHttpClient()
        self.base_url = base_url or self.DEFAULT_BASE_URL

    def fetch(self, query, timeout_seconds=15, request=None, source=None):
        request = dict(request or {})
        location = dict(request.get("location") or {})
        latitude = self._float(location.get("latitude"), "latitude")
        longitude = self._float(location.get("longitude"), "longitude")
        date_mode = request.get("date_mode") or self._date_mode(query)
        location_name = location.get("name") or self._location_name(location)

        url = self._build_url(latitude, longitude, forecast_days=2)
        payload = self.http_client.get_json(url, timeout_seconds=timeout_seconds)
        result = self._normalize(payload, latitude, longitude, location_name, date_mode)
        data = result.to_dict()
        data["endpoint"] = self.base_url
        data["query"] = str(query or "")
        return data

    def _build_url(self, latitude, longitude, forecast_days=2):
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": int(forecast_days),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
        return f"{self.base_url}?{urlencode(params)}"

    def _normalize(self, payload, latitude, longitude, location_name, date_mode):
        if not isinstance(payload, dict):
            raise RuntimeError("Open-Meteo retornou payload inválido.")
        daily = payload.get("daily")
        if not isinstance(daily, dict):
            raise RuntimeError("Open-Meteo não retornou dados diários.")

        times = daily.get("time") or []
        index = 1 if date_mode == "tomorrow" else 0
        if len(times) <= index:
            raise RuntimeError("Open-Meteo retornou previsão incompleta para a data solicitada.")

        forecast_date = times[index]
        weather_code = self._at(daily, "weather_code", index)
        temperature_min = self._at(daily, "temperature_2m_min", index)
        temperature_max = self._at(daily, "temperature_2m_max", index)
        precipitation_probability = self._at(daily, "precipitation_probability_max", index)
        summary = self._summary(weather_code, temperature_min, temperature_max, precipitation_probability)
        return WeatherResult(
            source_id="weather.open_meteo",
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            forecast_date=forecast_date,
            summary=summary,
            temperature_min=temperature_min,
            temperature_max=temperature_max,
            precipitation_probability=precipitation_probability,
            weather_code=weather_code,
            raw={
                "daily": daily,
                "timezone": payload.get("timezone"),
                "utc_offset_seconds": payload.get("utc_offset_seconds"),
                "generationtime_ms": payload.get("generationtime_ms"),
            },
        )

    def _summary(self, weather_code, temperature_min, temperature_max, precipitation_probability):
        description = self.WEATHER_CODE_PT_BR.get(weather_code, f"código climático {weather_code}")
        parts = [f"previsão de {description}"]
        if temperature_min is not None and temperature_max is not None:
            parts.append(f"mínima de {temperature_min:g}°C e máxima de {temperature_max:g}°C")
        elif temperature_min is not None:
            parts.append(f"mínima de {temperature_min:g}°C")
        elif temperature_max is not None:
            parts.append(f"máxima de {temperature_max:g}°C")
        if precipitation_probability is not None:
            parts.append(f"probabilidade máxima de precipitação de {precipitation_probability:g}%")
        return ", ".join(parts) + "."

    def _date_mode(self, query):
        normalized = str(query or "").lower()
        if "amanh" in normalized:
            return "tomorrow"
        return "today"

    def _location_name(self, location):
        city = str(location.get("city") or "").strip()
        state = str(location.get("state") or "").strip()
        country = str(location.get("country") or "").strip()
        parts = [part for part in (city, state, country) if part]
        return ", ".join(parts) or "localização configurada"

    def _float(self, value, field_name):
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Localização sem {field_name} válida para consultar clima.") from error

    def _at(self, daily, key, index):
        values = daily.get(key)
        if not isinstance(values, list) or len(values) <= index:
            return None
        return values[index]


def tomorrow_iso():
    return (date.today() + timedelta(days=1)).isoformat()
