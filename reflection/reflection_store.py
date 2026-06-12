import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class ReflectionEvent:
    source_message: str
    athena_response: str
    route: str = ""
    intent: str = ""
    target: str = ""
    issue_type: str = ""
    severity: str = "low"
    suspected_module: str = ""
    explanation: str = ""
    suggestion: str = ""
    suggested_tests: list = field(default_factory=list)
    requires_human_review: bool = True
    metadata: dict = field(default_factory=dict)
    critic_verdict: str = ""
    critic_confidence: float = 0.0
    accepted: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self):
        payload = asdict(self)
        if not isinstance(payload.get("suggested_tests"), list):
            payload["suggested_tests"] = [str(payload["suggested_tests"])]
        payload["requires_human_review"] = bool(payload.get("requires_human_review", True))
        payload["accepted"] = bool(payload.get("accepted", False))
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        if isinstance(clean.get("suggested_tests"), str):
            clean["suggested_tests"] = [clean["suggested_tests"]]
        return cls(**clean)


class ReflectionStore:
    """Append-only local store for Athena self-audit hypotheses."""

    def __init__(self, path="logs/reflection_events.jsonl", logger=None):
        self.path = path
        self.logger = logger
        self._lock = threading.RLock()
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def save(self, event):
        event = event if isinstance(event, ReflectionEvent) else ReflectionEvent.from_dict(event)
        payload = event.to_dict()
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as file:
                file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        if self.logger:
            self.logger.log("REFLECTION_EVENT", json.dumps(payload, ensure_ascii=False, default=str))
        return payload

    def list_recent(self, limit=20, issue_type=None, severity=None):
        if not os.path.exists(self.path):
            return []

        events = []
        with self._lock:
            with open(self.path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if issue_type and payload.get("issue_type") != issue_type:
                        continue
                    if severity and payload.get("severity") != severity:
                        continue
                    events.append(payload)
        return list(reversed(events[-int(limit):]))

    def count(self):
        if not os.path.exists(self.path):
            return 0
        with self._lock:
            with open(self.path, "r", encoding="utf-8") as file:
                return sum(1 for line in file if line.strip())
