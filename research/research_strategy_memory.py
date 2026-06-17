import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class ResearchStrategy:
    domain: str
    preferred_source: str = ""
    candidate_sources: list = field(default_factory=list)
    required_inputs: list = field(default_factory=list)
    evidence_required: bool = True
    freshness_ttl_seconds: int = 3600
    learned_from: str = "local_observation"
    confidence: float = 0.5
    status: str = "candidate"
    requires_human_review: bool = True
    success_count: int = 0
    failure_count: int = 0
    stale_reason: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self):
        payload = asdict(self)
        payload["domain"] = str(payload.get("domain") or "unknown_external")
        payload["preferred_source"] = str(payload.get("preferred_source") or "")
        payload["candidate_sources"] = list(payload.get("candidate_sources") or [])
        payload["required_inputs"] = list(payload.get("required_inputs") or [])
        payload["confidence"] = max(0.0, min(1.0, float(payload.get("confidence") or 0.0)))
        payload["status"] = _safe_status(payload.get("status"))
        payload["requires_human_review"] = bool(payload.get("requires_human_review"))
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        return cls(**clean)


class ResearchStrategyMemory:
    """Persistent procedural memory for how Athena should research domains."""

    def __init__(self, path=None, initial_strategies=None):
        self.path = path
        self._lock = threading.RLock()
        self._strategies = {}
        self._load()
        for strategy in initial_strategies or []:
            self.upsert(strategy)

    def upsert(self, strategy):
        strategy = strategy if isinstance(strategy, ResearchStrategy) else ResearchStrategy.from_dict(strategy)
        now = datetime.now().isoformat(timespec="seconds")
        existing = self._strategies.get(self._key(strategy.domain, strategy.preferred_source))
        if existing:
            created_at = existing.created_at
            merged = existing.to_dict()
            merged.update(strategy.to_dict())
            strategy = ResearchStrategy.from_dict(merged)
            strategy.created_at = created_at
        strategy.updated_at = now
        with self._lock:
            self._strategies[self._key(strategy.domain, strategy.preferred_source)] = strategy
            self._save()
        return strategy.to_dict()

    def get_active(self, domain):
        strategies = [
            strategy for strategy in self._strategies.values()
            if strategy.domain == domain and strategy.status == "active"
        ]
        strategies.sort(key=lambda item: (-item.confidence, item.preferred_source))
        return strategies[0].to_dict() if strategies else None

    def list(self, domain=None, status=None):
        with self._lock:
            strategies = list(self._strategies.values())
        if domain:
            strategies = [strategy for strategy in strategies if strategy.domain == domain]
        if status:
            strategies = [strategy for strategy in strategies if strategy.status == status]
        strategies.sort(key=lambda item: (item.domain, item.status, item.preferred_source))
        return [strategy.to_dict() for strategy in strategies]

    def mark_stale(self, domain, preferred_source="", reason=""):
        key = self._key(domain, preferred_source)
        with self._lock:
            strategy = self._strategies.get(key)
            if not strategy:
                return None
            strategy.status = "stale"
            strategy.stale_reason = str(reason or "stale").strip()
            strategy.updated_at = datetime.now().isoformat(timespec="seconds")
            self._save()
            return strategy.to_dict()

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        for item in payload.get("strategies", []) if isinstance(payload, dict) else []:
            strategy = ResearchStrategy.from_dict(item)
            self._strategies[self._key(strategy.domain, strategy.preferred_source)] = strategy

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {"strategies": [item.to_dict() for item in self._strategies.values()]}
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def _key(self, domain, preferred_source):
        return f"{str(domain or 'unknown_external')}::{str(preferred_source or '')}"


def _safe_status(status):
    status = str(status or "candidate").strip().lower()
    allowed = {"candidate", "needs_source", "needs_module", "needs_validation", "active", "failed", "stale", "rejected"}
    return status if status in allowed else "candidate"
