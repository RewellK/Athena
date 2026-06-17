import unicodedata

from location.location_store import LocationStore, UserLocation


class LocationManager:
    """Stores user location only with explicit local consent."""

    def __init__(self, store=None, settings=None):
        self.store = store or LocationStore()
        self.settings = settings

    def current(self):
        return self.store.get()

    def has_saved_location(self):
        return bool(self.current())

    def weather_location(self):
        location = self.current()
        if not location or location.get("consent_status") != "granted":
            return None
        if not self.has_coordinates(location):
            return None
        return self._weather_payload(location)

    def has_coordinates(self, location=None):
        location = location or self.current() or {}
        try:
            float(location.get("latitude"))
            float(location.get("longitude"))
            return True
        except (TypeError, ValueError):
            return False

    def save_from_text(self, text, source="user_provided", consent_status="granted"):
        parsed = self.parse_location_text(text)
        if not parsed.get("city"):
            return None
        precision = "coordinates" if parsed.get("latitude") is not None and parsed.get("longitude") is not None else "city"
        return self.store.save(UserLocation(
            city=parsed.get("city", ""),
            state=parsed.get("state", ""),
            country=parsed.get("country", ""),
            latitude=parsed.get("latitude"),
            longitude=parsed.get("longitude"),
            precision=precision,
            source=source,
            consent_status=consent_status,
        ))

    def save(self, city, state="", country="", latitude=None, longitude=None, source="user_provided", consent_status="granted"):
        precision = "coordinates" if latitude is not None and longitude is not None else "city"
        return self.store.save(UserLocation(
            city=str(city or "").strip(),
            state=str(state or "").strip(),
            country=str(country or "").strip(),
            latitude=latitude,
            longitude=longitude,
            precision=precision,
            source=source,
            consent_status=consent_status,
        ))

    def clear(self):
        return self.store.clear()

    def deny(self):
        self.store.clear()
        return self.store.save(UserLocation(
            precision="unknown",
            source="user_provided",
            consent_status="denied",
        ))

    def describe(self):
        location = self.current()
        if not location:
            return "Não tenho uma localização sua salva."
        if location.get("consent_status") == "denied":
            return "Você registrou que não quer salvar localização. Não vou usar localização padrão."
        label = self.location_label(location)
        coord_text = "com coordenadas" if self.has_coordinates(location) else "sem coordenadas"
        return (
            f"Tenho sua localização salva como {label}. "
            f"Precisão: {location.get('precision', 'unknown')} ({coord_text}). "
            f"Fonte: {location.get('source', 'unknown')}. Consentimento: {location.get('consent_status', 'not_requested')}."
        )

    def weather_missing_response(self):
        location = self.current()
        if location and location.get("consent_status") == "denied":
            return (
                "Você não autorizou salvar localização. Para consultar clima, posso usar uma cidade só quando você informar, "
                "mas não vou guardar nada sem consentimento."
            )
        if location and location.get("consent_status") == "granted" and not self.has_coordinates(location):
            label = self.location_label(location)
            return (
                f"Tenho sua localização salva como {label}, mas ainda não tenho coordenadas nem geocoder habilitado. "
                "Não vou inventar latitude/longitude. Posso criar uma proposta de módulo GeocodingConnector para transformar cidade em coordenadas com validação humana."
            )
        return (
            "Ainda não possuo uma localização padrão para clima. Para consultar o clima, preciso de uma localização. Posso usar uma cidade padrão? "
            "Se quiser salvar, diga: \"use São Paulo, SP como minha localização padrão\"."
        )

    def why_needed(self):
        return (
            "Eu preciso de localização para consultas de clima porque a fonte meteorológica usa cidade ou coordenadas. "
            "Eu não devo inventar sua cidade nem usar localização precisa sem consentimento. Você pode salvar, consultar ou apagar isso quando quiser."
        )

    def respond(self, operation, user_input=""):
        if operation == "location_status":
            return self.describe()
        if operation == "clear_location":
            previous = self.clear()
            if previous:
                return "Apaguei sua localização salva. Não vou usar localização padrão até você autorizar outra."
            return "Eu não tinha localização salva para apagar."
        if operation == "deny_location":
            self.deny()
            return "Entendi. Não vou salvar sua localização e não vou usar localização padrão sem você autorizar."
        if operation in {"why_location", "location_privacy"}:
            return self.why_needed()
        if operation in {"set_location", "set_default_location"}:
            saved = self.save_from_text(user_input, consent_status="granted")
            if not saved:
                return "Não consegui identificar a cidade. Pode me dizer no formato: cidade, estado, país?"
            response = f"Salvei sua localização padrão como {self.location_label(saved)}."
            if not self.has_coordinates(saved):
                response += (
                    " Ela ainda não tem coordenadas, então não vou consultar Open-Meteo com ela até haver coordenadas "
                    "ou um GeocodingConnector validado."
                )
            return response
        if operation == "one_time_location":
            parsed = self.parse_location_text(user_input)
            if not parsed.get("city"):
                return "Posso usar uma localização só agora, mas preciso que você informe cidade e estado."
            return (
                f"Posso usar {self.location_label(parsed)} só para esta conversa, mas na V12.9 ainda preciso de coordenadas "
                "ou de um GeocodingConnector validado para consultar clima sem inventar."
            )
        return "Ainda não reconheci esse comando de localização."

    def parse_location_text(self, text):
        original = str(text or "").strip()
        clean = self._strip_command_prefix(original)
        parts = [part.strip(" .") for part in clean.split(",") if part.strip(" .")]
        if not parts:
            return {}
        parsed = {
            "city": parts[0],
            "state": parts[1] if len(parts) > 1 else "",
            "country": parts[2] if len(parts) > 2 else "",
            "latitude": None,
            "longitude": None,
        }
        return parsed

    def location_label(self, location=None):
        location = location or self.current() or {}
        parts = [location.get("city", ""), location.get("state", ""), location.get("country", "")]
        return ", ".join(part for part in parts if part) or "localização não definida"

    def _weather_payload(self, location):
        return {
            "city": location.get("city", ""),
            "state": location.get("state", ""),
            "country": location.get("country", ""),
            "latitude": float(location.get("latitude")),
            "longitude": float(location.get("longitude")),
            "name": self.location_label(location),
        }

    def _strip_command_prefix(self, text):
        normalized = self._normalize(text)
        prefixes = [
            "minha localizacao e ",
            "minha localizacao eh ",
            "minha cidade e ",
            "minha cidade eh ",
            "use ",
            "usar ",
            "configure minha cidade padrao como ",
            "configure minha cidade padrao ",
            "configure minha localizacao padrao como ",
            "configure minha localizacao padrao ",
            "pode usar ",
        ]
        suffixes = [
            " como minha localizacao padrao",
            " como minha cidade padrao",
            " como localizacao padrao",
            " como cidade padrao",
            " so agora",
            " só agora",
        ]
        start = 0
        end = len(text)
        for prefix in prefixes:
            if normalized.startswith(prefix):
                start = len(prefix)
                break
        trimmed_normalized = normalized[start:]
        for suffix in suffixes:
            if trimmed_normalized.endswith(self._normalize(suffix)):
                end = start + len(trimmed_normalized) - len(self._normalize(suffix))
                break
        return text[start:end].strip(" .")

    def _normalize(self, text):
        normalized = unicodedata.normalize("NFD", str(text or "").lower())
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        for char in "?!;:":
            normalized = normalized.replace(char, " ")
        return " ".join(normalized.split())
