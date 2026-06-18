import json
import os
import threading
from datetime import datetime


class RuntimeAuditLog:
    def __init__(self, path="logs/runtime_audit.jsonl"):
        self.path = path
        self._lock = threading.RLock()

    def record(self, event_type, payload=None):
        entry = {
            "event_type": str(event_type or "runtime_event"),
            "payload": dict(payload or {}),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        if not self.path:
            return entry
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return entry
