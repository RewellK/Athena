import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256


TASK_STATUSES = {
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
    "awaiting_approval",
    "cancelled",
}


@dataclass
class PendingTask:
    type: str
    status: str = "pending"
    priority: int = 50
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    attempts: int = 0
    last_error: str = ""
    origin: str = "runtime"
    requires_user_approval: bool = False
    payload: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    dedup_key: str = ""

    def to_dict(self):
        payload = asdict(self)
        payload["status"] = payload.get("status") if payload.get("status") in TASK_STATUSES else "pending"
        payload["dedup_key"] = payload.get("dedup_key") or _task_dedup_key(payload)
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{key: value for key, value in payload.items() if key in known})


class PendingTaskRegistry:
    def __init__(self, path="logs/runtime_tasks.json"):
        self.path = path
        self._lock = threading.RLock()
        self._tasks = []
        self._load()

    def create(self, task_type, priority=50, origin="runtime", requires_user_approval=False, payload=None):
        task = PendingTask(
            type=task_type,
            priority=int(priority),
            origin=origin,
            requires_user_approval=bool(requires_user_approval),
            payload=dict(payload or {}),
        ).to_dict()
        with self._lock:
            existing = self._find_duplicate(task)
            if existing and existing.get("status") in {"pending", "running", "awaiting_approval"}:
                existing["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save()
                return dict(existing)
            self._tasks.append(task)
            self._save()
        return dict(task)

    def list(self, status=None, task_type=None, limit=50):
        with self._lock:
            items = list(self._tasks)
        if status:
            items = [item for item in items if item.get("status") == status]
        if task_type:
            items = [item for item in items if item.get("type") == task_type]
        items.sort(key=lambda item: (-int(item.get("priority") or 0), item.get("created_at", "")))
        return [dict(item) for item in items[: int(limit)]]

    def update_status(self, task_id, status, error=""):
        status = status if status in TASK_STATUSES else "pending"
        with self._lock:
            for task in self._tasks:
                if task.get("id") == task_id:
                    task["status"] = status
                    task["updated_at"] = datetime.now().isoformat(timespec="seconds")
                    if status in {"running", "failed"}:
                        task["attempts"] = int(task.get("attempts") or 0) + 1
                    if error:
                        task["last_error"] = str(error)
                    self._save()
                    return dict(task)
        return None

    def counts(self):
        counts = {}
        with self._lock:
            for task in self._tasks:
                status = task.get("status", "pending")
                counts[status] = counts.get(status, 0) + 1
        return counts

    def _find_duplicate(self, task):
        key = task.get("dedup_key") or _task_dedup_key(task)
        for item in self._tasks:
            item["dedup_key"] = item.get("dedup_key") or _task_dedup_key(item)
            if item.get("dedup_key") == key:
                return item
        return None

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        self._tasks = list(payload.get("tasks", [])) if isinstance(payload, dict) else []

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"tasks": self._tasks}, file, ensure_ascii=False, indent=2)


def _task_dedup_key(payload):
    raw = json.dumps(
        {
            "type": payload.get("type"),
            "origin": payload.get("origin"),
            "payload": payload.get("payload") or {},
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return sha256(raw.encode("utf-8")).hexdigest()
