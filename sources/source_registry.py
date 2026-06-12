import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime


SOURCE_STATUSES = {
    "candidate",
    "pending_validation",
    "disabled",
    "enabled",
    "failed_validation",
    "rejected",
    "deprecated",
}


@dataclass
class SourceProposal:
    domain: str
    name: str
    source_type: str = "website"
    url: str = ""
    reason: str = ""
    requires_api_key: str = "unknown"
    supports_api: str = "unknown"
    connector_type: str = "generic_website_stub"
    trust_level: str = "unverified"
    freshness_ttl_seconds: int = 3600
    status: str = "candidate"
    discovered_by: str = "source_discovery"
    validation_status: str = "not_validated"
    requires_human_approval: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self):
        payload = asdict(self)
        payload["status"] = _safe_status(payload.get("status"), default="candidate")
        payload["requires_human_approval"] = True
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        payload["status"] = _safe_status(payload.get("status"), default="candidate")
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        return cls(**clean)


@dataclass
class SourceRecord:
    source_id: str
    domain: str
    name: str
    source_type: str = "website"
    url: str = ""
    reason: str = ""
    requires_api_key: str = "unknown"
    supports_api: str = "unknown"
    connector_type: str = "generic_website_stub"
    trust_level: str = "unverified"
    freshness_ttl_seconds: int = 3600
    status: str = "candidate"
    enabled: bool = False
    discovered_by: str = "source_discovery"
    validation_status: str = "not_validated"
    requires_human_approval: bool = True
    credential_key: str = ""
    last_success_at: str = ""
    last_failure_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self):
        payload = asdict(self)
        payload["status"] = _safe_status(payload.get("status"), default="candidate")
        payload["enabled"] = bool(payload.get("enabled")) and payload["status"] == "enabled"
        payload["requires_human_approval"] = True
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        payload["status"] = _safe_status(payload.get("status"), default="candidate")
        payload["enabled"] = bool(payload.get("enabled")) and payload["status"] == "enabled"
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        return cls(**clean)


class SourceRegistry:
    """Local source catalog. Candidate sources are never enabled automatically."""

    def __init__(self, path=None, initial_sources=None, logger=None):
        self.path = path
        self.logger = logger
        self._lock = threading.RLock()
        self._sources = {}
        self._load()
        for source in initial_sources or []:
            record = source if isinstance(source, SourceRecord) else SourceRecord.from_dict(source)
            self._sources[record.source_id] = record

    def list_sources(self, domain=None, status=None):
        with self._lock:
            records = list(self._sources.values())
        if domain:
            records = [source for source in records if source.domain == domain]
        if status:
            records = [source for source in records if source.status == status]
        return [record.to_dict() for record in sorted(records, key=lambda item: item.source_id)]

    def get(self, source_id):
        with self._lock:
            record = self._sources.get(source_id)
        return record.to_dict() if record else None

    def find_enabled(self, domain):
        with self._lock:
            records = [
                source for source in self._sources.values()
                if source.domain == domain and source.status == "enabled" and source.enabled
            ]
        return [record.to_dict() for record in sorted(records, key=lambda item: item.source_id)]

    def has_enabled_source(self, domain):
        return bool(self.find_enabled(domain))

    def add_candidate(self, proposal):
        proposal = proposal if isinstance(proposal, SourceProposal) else SourceProposal.from_dict(proposal)
        source_id = self._make_source_id(proposal.domain, proposal.name)
        now = datetime.now().isoformat(timespec="seconds")
        record = SourceRecord(
            source_id=source_id,
            domain=proposal.domain,
            name=proposal.name,
            source_type=proposal.source_type,
            url=proposal.url,
            reason=proposal.reason,
            requires_api_key=proposal.requires_api_key,
            supports_api=proposal.supports_api,
            connector_type=proposal.connector_type,
            trust_level=proposal.trust_level,
            freshness_ttl_seconds=proposal.freshness_ttl_seconds,
            status="candidate",
            enabled=False,
            discovered_by=proposal.discovered_by,
            validation_status=proposal.validation_status,
            requires_human_approval=True,
            created_at=proposal.created_at or now,
            updated_at=now,
        )
        with self._lock:
            existing = self._sources.get(source_id)
            if existing and existing.status != "rejected":
                return existing.to_dict()
            self._sources[source_id] = record
            self._save()
        return record.to_dict()

    def upsert(self, source):
        record = source if isinstance(source, SourceRecord) else SourceRecord.from_dict(source)
        with self._lock:
            self._sources[record.source_id] = record
            self._save()
        return record.to_dict()

    def update_status(self, source_id, status, validation_status=None):
        status = _safe_status(status)
        with self._lock:
            record = self._sources.get(source_id)
            if not record:
                return None
            record.status = status
            record.enabled = status == "enabled" and record.validation_status == "passed"
            if validation_status is not None:
                record.validation_status = str(validation_status)
                record.enabled = record.status == "enabled" and record.validation_status == "passed"
            record.updated_at = datetime.now().isoformat(timespec="seconds")
            self._save()
            return record.to_dict()

    def enable(self, source_id):
        with self._lock:
            record = self._sources.get(source_id)
            if not record:
                return None
            if record.validation_status != "passed":
                record.status = "pending_validation"
                record.enabled = False
                record.updated_at = datetime.now().isoformat(timespec="seconds")
                self._save()
                return record.to_dict()
            record.status = "enabled"
            record.enabled = True
            record.updated_at = datetime.now().isoformat(timespec="seconds")
            self._save()
            return record.to_dict()

    def reject(self, source_id):
        return self.update_status(source_id, "rejected")

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        sources = payload.get("sources", []) if isinstance(payload, dict) else []
        for source in sources:
            record = SourceRecord.from_dict(source)
            self._sources[record.source_id] = record

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {"sources": [source.to_dict() for source in sorted(self._sources.values(), key=lambda item: item.source_id)]}
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def _make_source_id(self, domain, name):
        return f"{_slug(domain)}.{_slug(name)}"


def _safe_status(status, default="candidate"):
    status = str(status or default).strip().lower()
    return status if status in SOURCE_STATUSES else default


def _slug(text):
    text = str(text or "").strip().lower()
    chars = []
    previous_dash = False
    for char in text:
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("_")
            previous_dash = True
    return "".join(chars).strip("_") or "source"
