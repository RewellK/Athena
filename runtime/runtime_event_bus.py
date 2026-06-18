from dataclasses import asdict, dataclass, field
from datetime import datetime
import threading
import uuid


@dataclass
class RuntimeEvent:
    event_type: str
    payload: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self):
        return asdict(self)


class RuntimeEventBus:
    def __init__(self, audit_log=None, max_history=200):
        self.audit_log = audit_log
        self.max_history = int(max_history)
        self._subscribers = {}
        self._history = []
        self._lock = threading.RLock()

    def subscribe(self, event_type, callback):
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event_type, payload=None):
        event = RuntimeEvent(event_type=event_type, payload=dict(payload or {})).to_dict()
        with self._lock:
            self._history.append(event)
            self._history = self._history[-self.max_history :]
            subscribers = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))
        if self.audit_log:
            self.audit_log.record(event_type, event.get("payload"))
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                continue
        return event

    def history(self, limit=50, event_type=None):
        with self._lock:
            events = list(self._history)
        if event_type:
            events = [event for event in events if event.get("event_type") == event_type]
        return events[-int(limit) :]
