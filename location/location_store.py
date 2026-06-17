import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class UserLocation:
    city: str = ""
    state: str = ""
    country: str = ""
    latitude: float = None
    longitude: float = None
    precision: str = "unknown"
    source: str = "user_provided"
    consent_status: str = "not_requested"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    expires_at: str = ""

    def to_dict(self):
        payload = asdict(self)
        payload["precision"] = _safe_precision(payload.get("precision"), payload.get("latitude"), payload.get("longitude"))
        payload["consent_status"] = _safe_consent(payload.get("consent_status"))
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        return cls(**clean)


class LocationStore:
    def __init__(self, path=None):
        self.path = path
        self._lock = threading.RLock()
        self._location = None
        self._load()

    def get(self):
        with self._lock:
            return dict(self._location) if self._location else None

    def save(self, location):
        location = location if isinstance(location, UserLocation) else UserLocation.from_dict(location)
        payload = location.to_dict()
        now = datetime.now().isoformat(timespec="seconds")
        if not payload.get("created_at"):
            payload["created_at"] = now
        payload["updated_at"] = now
        with self._lock:
            self._location = payload
            self._save()
        return dict(payload)

    def clear(self):
        with self._lock:
            previous = dict(self._location) if self._location else None
            self._location = None
            self._save()
        return previous

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        location = payload.get("location") if isinstance(payload, dict) else None
        self._location = dict(location) if isinstance(location, dict) else None

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"location": self._location}, file, ensure_ascii=False, indent=2)


def _safe_consent(value):
    value = str(value or "not_requested").strip().lower()
    return value if value in {"granted", "not_requested", "denied"} else "not_requested"


def _safe_precision(value, latitude=None, longitude=None):
    value = str(value or "").strip().lower()
    if value in {"city", "coordinates", "unknown"}:
        return value
    return "coordinates" if latitude is not None and longitude is not None else "city"
