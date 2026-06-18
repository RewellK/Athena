import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class CommandSession:
    mode: str
    status: str = "active"
    scope: str = "general"
    policy: dict = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    ended_at: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self):
        return asdict(self)


class CommandSessionStore:
    def __init__(self, path=None):
        self.path = path
        self._lock = threading.RLock()
        self._sessions = []
        self._load()

    def start(self, mode, scope="general", policy=None):
        session = CommandSession(mode=mode, scope=scope, policy=dict(policy or {})).to_dict()
        with self._lock:
            self._sessions.append(session)
            self._save()
        return dict(session)

    def end(self, mode):
        with self._lock:
            for session in reversed(self._sessions):
                if session.get("mode") == mode and session.get("status") == "active":
                    session["status"] = "completed"
                    session["ended_at"] = datetime.now().isoformat(timespec="seconds")
                    self._save()
                    return dict(session)
        return None

    def active(self, mode=None):
        with self._lock:
            sessions = [item for item in self._sessions if item.get("status") == "active"]
        if mode:
            sessions = [item for item in sessions if item.get("mode") == mode]
        return [dict(item) for item in sessions]

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        self._sessions = list(payload.get("sessions", [])) if isinstance(payload, dict) else []

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"sessions": self._sessions}, file, ensure_ascii=False, indent=2)
