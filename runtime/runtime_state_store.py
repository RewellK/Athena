import json
import os
import threading
from datetime import datetime

from runtime.runtime_state import RuntimeState, new_state


class RuntimeStateStore:
    def __init__(self, path="logs/runtime_state.json"):
        self.path = path
        self._lock = threading.RLock()
        self._payload = self._load()

    def snapshot(self):
        with self._lock:
            return dict(self._payload)

    def state(self):
        return RuntimeState.from_dict(self.snapshot().get("state") or {})

    def set_state(self, name, reason="", current_task=""):
        state = new_state(name, reason=reason, current_task=current_task).to_dict()
        with self._lock:
            self._payload["state"] = state
            self._payload["updated_at"] = state["updated_at"]
            self._save()
        return dict(state)

    def update(self, **changes):
        with self._lock:
            self._payload.update(changes)
            self._payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self._save()
            return dict(self._payload)

    def heartbeat(self):
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            self._payload["last_heartbeat_at"] = now
            self._payload["updated_at"] = now
            state = dict(self._payload.get("state") or new_state("idle").to_dict())
            state["updated_at"] = now
            self._payload["state"] = state
            self._save()
        return now

    def _load(self):
        if self.path and os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as file:
                    payload = json.load(file)
                if isinstance(payload, dict):
                    payload.setdefault("state", new_state("offline").to_dict())
                    return payload
            except (OSError, json.JSONDecodeError):
                pass
        now = datetime.now().isoformat(timespec="seconds")
        return {
            "state": new_state("offline").to_dict(),
            "session_started_at": "",
            "last_heartbeat_at": "",
            "last_shutdown_at": "",
            "last_error": "",
            "paused": False,
            "safe_mode": False,
            "safe_mode_reason": "",
            "tasks_in_progress": [],
            "pending_snapshot": {},
            "created_at": now,
            "updated_at": now,
        }

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temp_path = self.path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(self._payload, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.path)
