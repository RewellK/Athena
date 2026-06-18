import json
import os
import threading
import uuid
from datetime import date, datetime


class DayMemoryBuffer:
    def __init__(self, path=None, retention_policy=None):
        self.path = path
        self.retention_policy = retention_policy or {
            "raw_retention": "short",
            "confirmed_memory_requires_approval": True,
        }
        self._lock = threading.RLock()
        self._buffers = {}
        self._load()

    def add_entry(
        self,
        content,
        source="conversation",
        context_type="conversation",
        sensitivity_level="low",
        candidate_importance=0.2,
        linked_conversation_id="",
        linked_runtime_state="",
        tags=None,
        day=None,
    ):
        day = day or date.today().isoformat()
        entry = {
            "id": uuid.uuid4().hex,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "source": str(source or "conversation"),
            "content": str(content or ""),
            "context_type": str(context_type or "unknown"),
            "sensitivity_level": str(sensitivity_level or "low"),
            "candidate_importance": float(candidate_importance or 0),
            "linked_conversation_id": str(linked_conversation_id or ""),
            "linked_runtime_state": str(linked_runtime_state or ""),
            "tags": list(tags or []),
        }
        with self._lock:
            buffer = self._buffer_locked(day)
            buffer["entries"].append(entry)
            buffer["updated_at"] = entry["timestamp"]
            self._save()
        return dict(entry)

    def entries(self, day=None, limit=200):
        day = day or date.today().isoformat()
        with self._lock:
            buffer = self._buffer_locked(day)
            return [dict(item) for item in buffer.get("entries", [])[-int(limit) :]]

    def mark_studying(self, day=None):
        return self._set_status(day or date.today().isoformat(), "studying")

    def mark_reviewed(self, review_id="", day=None):
        day = day or date.today().isoformat()
        with self._lock:
            buffer = self._buffer_locked(day)
            buffer["status"] = "reviewed"
            buffer["reviewed"] = True
            buffer["review_id"] = review_id
            buffer["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self._save()
            return dict(buffer)

    def archive(self, day=None):
        return self._set_status(day or date.today().isoformat(), "archived")

    def discard(self, day=None):
        return self._set_status(day or date.today().isoformat(), "discarded")

    def summary(self, day=None):
        day = day or date.today().isoformat()
        with self._lock:
            buffer = self._buffer_locked(day)
            return {
                "id": buffer.get("id"),
                "date": day,
                "entries": len(buffer.get("entries", [])),
                "status": buffer.get("status", "open"),
                "reviewed": bool(buffer.get("reviewed")),
                "review_id": buffer.get("review_id", ""),
            }

    def _set_status(self, day, status):
        with self._lock:
            buffer = self._buffer_locked(day)
            buffer["status"] = status
            buffer["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self._save()
            return dict(buffer)

    def _buffer_locked(self, day):
        if day not in self._buffers:
            now = datetime.now().isoformat(timespec="seconds")
            self._buffers[day] = {
                "id": uuid.uuid4().hex,
                "date": day,
                "created_at": now,
                "updated_at": now,
                "entries": [],
                "status": "open",
                "retention_policy": dict(self.retention_policy),
                "reviewed": False,
                "review_id": "",
            }
        return self._buffers[day]

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        self._buffers = dict(payload.get("buffers", {})) if isinstance(payload, dict) else {}

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"buffers": self._buffers}, file, ensure_ascii=False, indent=2)
