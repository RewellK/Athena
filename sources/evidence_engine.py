import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

from sources.freshness_engine import FreshnessEngine
from sources.source_trust_engine import SourceTrustEngine


@dataclass
class EvidenceRecord:
    source_id: str
    source_name: str
    domain: str
    query: str
    fetched_at: str
    valid_until: str
    confidence: str = "medium"
    raw_summary: dict = field(default_factory=dict)
    url: str = ""
    license_or_notes: str = ""
    freshness_ttl_seconds: int = 0
    trust: str = ""
    location: str = ""
    forecast_date: str = ""
    result_summary: str = ""
    evidence_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    evidence_type: str = "external_source"

    def to_dict(self):
        return asdict(self)


class EvidenceEngine:
    """Creates evidence only from enabled and validated sources."""

    def __init__(self, path=None, freshness_engine=None, trust_engine=None, logger=None):
        self.path = path
        self.freshness_engine = freshness_engine or FreshnessEngine()
        self.trust_engine = trust_engine or SourceTrustEngine()
        self.logger = logger
        self._lock = threading.RLock()
        self._records = []
        self._load()

    def can_create_trusted_evidence(self, source):
        return self.trust_engine.can_support_factual_answer(source)

    def create_record(self, source, query, raw_summary, confidence="medium", url=None, notes=""):
        source = dict(source or {})
        if not self.can_create_trusted_evidence(source):
            raise ValueError("Fonte precisa estar enabled, validada e confiável antes de gerar EvidenceRecord.")
        fetched_at = datetime.now().isoformat(timespec="seconds")
        ttl = self.freshness_engine.ttl_for(source.get("domain", "general_web"), source)
        record = EvidenceRecord(
            source_id=source.get("source_id", ""),
            source_name=source.get("name", ""),
            domain=source.get("domain", "general_web"),
            query=str(query or ""),
            fetched_at=fetched_at,
            valid_until=self.freshness_engine.valid_until(fetched_at, source.get("domain", "general_web"), source),
            confidence=confidence,
            raw_summary=dict(raw_summary or {}),
            url=url if url is not None else source.get("url", ""),
            license_or_notes=notes,
            freshness_ttl_seconds=ttl,
            trust=source.get("trust_level", ""),
            location=str((raw_summary or {}).get("location_name") or ""),
            forecast_date=str((raw_summary or {}).get("forecast_date") or ""),
            result_summary=str((raw_summary or {}).get("summary") or ""),
        )
        with self._lock:
            self._records.append(record.to_dict())
            self._save()
        return record.to_dict()

    def unverified_note(self, source_or_proposal, query):
        source = dict(source_or_proposal or {})
        return {
            "note_type": "unverified_source_note",
            "domain": source.get("domain", "unknown_external"),
            "source_name": source.get("name", "fonte candidata"),
            "query": str(query or ""),
            "status": source.get("status", "candidate"),
            "trust_level": source.get("trust_level", "unverified"),
            "can_support_factual_answer": False,
            "requires_human_review": True,
        }

    def list_records(self, limit=20):
        with self._lock:
            return list(reversed(self._records[-int(limit):]))

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        self._records.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            self._records = []

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            for record in self._records:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
