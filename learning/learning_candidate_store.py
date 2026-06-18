import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256


CANDIDATE_STATUSES = {
    "candidate",
    "approved",
    "rejected",
    "edited",
    "promoted",
    "discarded",
    "rejected_by_policy",
}


@dataclass
class LearningCandidate:
    session_id: str
    candidate_type: str
    content: str
    reason: str
    confidence: float = 0.45
    source_excerpt: str = ""
    suggested_destination: str = ""
    risk_level: str = "low"
    status: str = "candidate"
    requires_human_review: bool = True
    source: str = "learning_session"
    metadata: dict = field(default_factory=dict)
    edit_history: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    dedup_key: str = ""

    def to_dict(self):
        payload = asdict(self)
        payload["status"] = payload.get("status") if payload.get("status") in CANDIDATE_STATUSES else "candidate"
        payload["requires_human_review"] = True
        payload["dedup_key"] = payload.get("dedup_key") or _candidate_dedup_key(payload)
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{key: value for key, value in payload.items() if key in known})


class LearningCandidateStore:
    def __init__(self, path=None):
        self.path = path
        self._lock = threading.RLock()
        self._candidates = []
        self._load()

    def save(self, candidate):
        candidate = candidate if isinstance(candidate, LearningCandidate) else LearningCandidate.from_dict(candidate)
        payload = candidate.to_dict()
        with self._lock:
            existing = self._find_existing(payload)
            if existing and existing.get("status") not in {"rejected", "discarded", "promoted"}:
                existing["updated_at"] = datetime.now().isoformat(timespec="seconds")
                existing["metadata"] = {**dict(existing.get("metadata") or {}), "deduplicated": True}
                self._save()
                return dict(existing)
            self._candidates.append(payload)
            self._save()
        return dict(payload)

    def list(self, status=None, session_id=None, limit=50, include_promoted=True):
        with self._lock:
            items = list(self._candidates)
        if status:
            if isinstance(status, (set, list, tuple)):
                allowed = set(status)
                items = [item for item in items if item.get("status") in allowed]
            else:
                items = [item for item in items if item.get("status") == status]
        if session_id:
            items = [item for item in items if item.get("session_id") == session_id]
        if not include_promoted:
            items = [item for item in items if item.get("status") != "promoted"]
        return [dict(item) for item in items[-int(limit) :]]

    def count(self, status=None):
        return len(self.list(status=status, limit=100000))

    def update_status(self, identifier, status):
        status = status if status in CANDIDATE_STATUSES else "candidate"
        with self._lock:
            candidate = self._resolve_locked(identifier)
            if not candidate:
                return None
            candidate["status"] = status
            candidate["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self._save()
            return dict(candidate)

    def edit(self, identifier, new_content):
        with self._lock:
            candidate = self._resolve_locked(identifier)
            if not candidate:
                return None
            history = list(candidate.get("edit_history") or [])
            history.append({
                "previous_content": candidate.get("content", ""),
                "edited_at": datetime.now().isoformat(timespec="seconds"),
            })
            candidate["content"] = str(new_content or "").strip()
            candidate["status"] = "edited"
            candidate["edit_history"] = history
            candidate["updated_at"] = datetime.now().isoformat(timespec="seconds")
            candidate["dedup_key"] = _candidate_dedup_key(candidate)
            self._save()
            return dict(candidate)

    def resolve(self, identifier):
        with self._lock:
            candidate = self._resolve_locked(identifier)
            return dict(candidate) if candidate else None

    def _resolve_locked(self, identifier):
        identifier = str(identifier or "").strip()
        if not identifier:
            return None
        if identifier.isdigit():
            visible = [
                item
                for item in self._candidates
                if item.get("status") in {"candidate", "approved", "edited", "rejected"}
            ]
            index = int(identifier) - 1
            if 0 <= index < len(visible):
                return visible[index]
        for item in self._candidates:
            if item.get("id") == identifier:
                return item
        return None

    def _find_existing(self, payload):
        key = payload.get("dedup_key") or _candidate_dedup_key(payload)
        for item in self._candidates:
            item["dedup_key"] = item.get("dedup_key") or _candidate_dedup_key(item)
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
        self._candidates = list(payload.get("candidates", [])) if isinstance(payload, dict) else []

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"candidates": self._candidates}, file, ensure_ascii=False, indent=2)


def _candidate_dedup_key(payload):
    raw = "|".join(
        [
            str(payload.get("candidate_type") or "").strip().lower(),
            str(payload.get("suggested_destination") or "").strip().lower(),
            _normalize(payload.get("content")),
        ]
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _normalize(text):
    return " ".join(str(text or "").strip().lower().split())
