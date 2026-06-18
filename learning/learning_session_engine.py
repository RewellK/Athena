import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class LearningSession:
    status: str = "active"
    scope: str = "current_conversation"
    source: str = "user_command"
    use_llm_teacher: bool = False
    requires_review: bool = True
    created_candidates_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    messages: list = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    ended_at: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self):
        payload = asdict(self)
        payload["requires_review"] = True
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{key: value for key, value in payload.items() if key in known})


class LearningSessionEngine:
    def __init__(self, path=None, candidate_store=None):
        self.path = path
        self.candidate_store = candidate_store
        self._lock = threading.RLock()
        self._sessions = []
        self._active_session_id = ""
        self._load()

    def start(self, scope="current_conversation", use_llm_teacher=False):
        with self._lock:
            active = self._active_locked()
            if active:
                return dict(active)
            session = LearningSession(scope=scope, use_llm_teacher=bool(use_llm_teacher)).to_dict()
            self._sessions.append(session)
            self._active_session_id = session["id"]
            self._save()
            return dict(session)

    def stop(self):
        with self._lock:
            active = self._active_locked()
            if not active:
                return None
            active["status"] = "completed"
            active["ended_at"] = datetime.now().isoformat(timespec="seconds")
            self._active_session_id = ""
            self._save()
            return dict(active)

    def pause(self):
        with self._lock:
            active = self._active_locked()
            if not active:
                return None
            active["status"] = "paused"
            self._save()
            return dict(active)

    def resume(self):
        with self._lock:
            active = self._active_locked(include_paused=True)
            if not active:
                return None
            active["status"] = "active"
            self._active_session_id = active["id"]
            self._save()
            return dict(active)

    def active_session(self):
        with self._lock:
            active = self._active_locked()
            return dict(active) if active else None

    def list_sessions(self, status=None, limit=20):
        with self._lock:
            items = list(self._sessions)
        if status:
            items = [item for item in items if item.get("status") == status]
        return [dict(item) for item in items[-int(limit) :]]

    def record_message(self, role, content, metadata=None):
        with self._lock:
            active = self._active_locked()
            if not active:
                return None
            message = {
                "role": str(role or "user"),
                "content": str(content or ""),
                "metadata": dict(metadata or {}),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "processed": False,
            }
            active.setdefault("messages", []).append(message)
            self._save()
            return dict(message)

    def unprocessed_messages(self, session_id):
        with self._lock:
            session = self._find_locked(session_id)
            if not session:
                return []
            return [dict(item) for item in session.get("messages", []) if not item.get("processed")]

    def mark_messages_processed(self, session_id, count=None):
        with self._lock:
            session = self._find_locked(session_id)
            if not session:
                return 0
            marked = 0
            for message in session.get("messages", []):
                if message.get("processed"):
                    continue
                message["processed"] = True
                marked += 1
                if count is not None and marked >= int(count):
                    break
            self._save()
            return marked

    def update_counts(self):
        if not self.candidate_store:
            return None
        with self._lock:
            for session in self._sessions:
                session_id = session.get("id")
                session["created_candidates_count"] = len(self.candidate_store.list(session_id=session_id, limit=100000))
                session["approved_count"] = len(self.candidate_store.list(status="approved", session_id=session_id, limit=100000))
                session["rejected_count"] = len(self.candidate_store.list(status="rejected", session_id=session_id, limit=100000))
            self._save()
        return True

    def _active_locked(self, include_paused=False):
        if self._active_session_id:
            session = self._find_locked(self._active_session_id)
            if session and (session.get("status") == "active" or include_paused and session.get("status") == "paused"):
                return session
        for session in reversed(self._sessions):
            if session.get("status") == "active" or include_paused and session.get("status") == "paused":
                self._active_session_id = session.get("id", "")
                return session
        return None

    def _find_locked(self, session_id):
        for session in self._sessions:
            if session.get("id") == session_id:
                return session
        return None

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(payload, dict):
            self._sessions = list(payload.get("sessions", []))
            self._active_session_id = payload.get("active_session_id", "")

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(
                {"active_session_id": self._active_session_id, "sessions": self._sessions},
                file,
                ensure_ascii=False,
                indent=2,
            )
