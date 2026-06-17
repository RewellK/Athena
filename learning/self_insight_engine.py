import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256


@dataclass
class SelfInsight:
    insight_type: str
    content: str
    suspected_module: str = ""
    suggested_action: str = ""
    suggested_test: str = ""
    source: str = "reflection_event"
    source_id: str = ""
    status: str = "pending_human_review"
    confidence: float = 0.5
    requires_human_review: bool = True
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    insight_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    dedup_key: str = ""
    occurrence_count: int = 1
    first_seen_at: str = ""
    last_seen_at: str = ""
    related_event_ids: list = field(default_factory=list)

    def to_dict(self):
        payload = asdict(self)
        payload["dedup_key"] = payload.get("dedup_key") or _insight_dedup_key(payload)
        payload["occurrence_count"] = int(payload.get("occurrence_count") or 1)
        payload["first_seen_at"] = payload.get("first_seen_at") or payload.get("created_at")
        payload["last_seen_at"] = payload.get("last_seen_at") or payload.get("updated_at")
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{key: value for key, value in payload.items() if key in known})


class SelfInsightStore:
    def __init__(self, path=None):
        self.path = path
        self._lock = threading.RLock()
        self._insights = []
        self._load()

    def save(self, insight):
        insight = insight if isinstance(insight, SelfInsight) else SelfInsight.from_dict(insight)
        payload = insight.to_dict()
        with self._lock:
            existing = self._find_existing(payload)
            if existing:
                existing["occurrence_count"] = int(existing.get("occurrence_count") or 1) + 1
                existing["last_seen_at"] = datetime.now().isoformat(timespec="seconds")
                existing["updated_at"] = existing["last_seen_at"]
                existing["deduplicated"] = True
                event_id = payload.get("source_id")
                related = list(existing.get("related_event_ids") or [])
                if event_id and event_id not in related:
                    related.append(event_id)
                existing["related_event_ids"] = related
                self._save()
                return dict(existing)
            self._insights.append(payload)
            self._save()
        return payload

    def list(self, status=None, limit=20):
        with self._lock:
            items = list(self._insights)
        if status:
            items = [item for item in items if item.get("status") == status]
        return list(reversed(items[-int(limit):]))

    def update_status(self, insight_id, status):
        with self._lock:
            for item in self._insights:
                if item.get("insight_id") == insight_id:
                    item["status"] = status
                    item["requires_human_review"] = status not in {"confirmed", "rejected"}
                    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
                    self._save()
                    return dict(item)
        return None

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        self._insights = list(payload.get("insights", [])) if isinstance(payload, dict) else []

    def _find_existing(self, payload):
        dedup_key = payload.get("dedup_key") or _insight_dedup_key(payload)
        for item in self._insights:
            item["dedup_key"] = item.get("dedup_key") or _insight_dedup_key(item)
            if item.get("dedup_key") == dedup_key:
                return item
        return None

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"insights": self._insights}, file, ensure_ascii=False, indent=2)


class SelfInsightEngine:
    """Turns local evidence into Athena self-insight hypotheses."""

    def __init__(self, store=None):
        self.store = store or SelfInsightStore()

    def create_from_reflection_event(self, event):
        event = event.to_dict() if hasattr(event, "to_dict") else dict(event or {})
        content = event.get("explanation") or f"Observei uma possível falha do tipo {event.get('issue_type', 'unknown')}."
        suggested_tests = event.get("suggested_tests") or []
        return self.store.save(SelfInsight(
            insight_type="weakness",
            content=content,
            suspected_module=event.get("suspected_module", ""),
            suggested_action=event.get("suggestion", ""),
            suggested_test=suggested_tests[0] if suggested_tests else "",
            source="reflection_event",
            source_id=event.get("event_id", ""),
            status="pending_human_review",
            confidence=0.6,
            requires_human_review=True,
            metadata={"issue_type": event.get("issue_type"), "severity": event.get("severity")},
            related_event_ids=[event.get("event_id")] if event.get("event_id") else [],
        ))

    def create_from_teacher_insight(self, insight):
        insight = dict(insight or {})
        return self.store.save(SelfInsight(
            insight_type=insight.get("insight_type", "learning_hypothesis"),
            content=insight.get("summary") or insight.get("suggested_action") or "Insight candidato do LLMTeacher.",
            suspected_module=insight.get("suspected_module", ""),
            suggested_action=insight.get("suggested_action", ""),
            suggested_test=insight.get("suggested_test", ""),
            source="llm_teacher",
            source_id=insight.get("insight_id", ""),
            status="pending_human_review",
            confidence=float(insight.get("confidence", 0.35) or 0.35),
            requires_human_review=True,
            metadata=insight,
        ))

    def create_learning_to_learn_insight(self, source, content, suggested_action="", suggested_test=""):
        return self.store.save(SelfInsight(
            insight_type="learning_strategy",
            content=content,
            suspected_module="LearningWorkbench/TeacherLoop",
            suggested_action=suggested_action,
            suggested_test=suggested_test,
            source=source,
            status="pending_human_review",
            confidence=0.55,
            requires_human_review=True,
            metadata={"learning_about_learning": True},
        ))

    def create_from_capability_gap(self, gap, module_proposal=None):
        gap = dict(gap or {})
        module_proposal = dict(module_proposal or {})
        title = module_proposal.get("title", "módulo futuro")
        domain = gap.get("domain", "unknown_external")
        return self.store.save(SelfInsight(
            insight_type="missing_capability",
            content=(
                f"Não tenho capacidade/módulo validado para {domain}. "
                f"Proposta sugerida: {title}."
            ),
            suspected_module="CapabilityGapEngine/SourceManager",
            suggested_action=f"Revisar proposta {title} e validar fontes antes de implementar.",
            suggested_test=(module_proposal.get("suggested_tests") or ["Pedido sem módulo validado não deve inventar resposta."])[0],
            source="user_request",
            source_id=module_proposal.get("proposal_id", ""),
            status="pending_human_review",
            confidence=0.6,
            requires_human_review=True,
            metadata={"gap": gap, "module_proposal": module_proposal},
        ))

    def list_pending(self, limit=20):
        return self.store.list(status="pending_human_review", limit=limit)

    def approve(self, insight_id):
        return self.store.update_status(insight_id, "confirmed")

    def reject(self, insight_id):
        return self.store.update_status(insight_id, "rejected")


def _insight_dedup_key(payload):
    metadata = dict(payload.get("metadata") or {})
    gap = dict(metadata.get("gap") or {})
    module_proposal = dict(metadata.get("module_proposal") or {})
    if str(payload.get("insight_type") or "").strip().lower() == "missing_capability":
        parts = [
            "missing_capability",
            str(gap.get("domain") or "").strip().lower(),
            str(module_proposal.get("title") or "").strip().lower(),
        ]
        return sha256("|".join(parts).encode("utf-8")).hexdigest()
    parts = [
        str(payload.get("insight_type") or "").strip().lower(),
        str(payload.get("suspected_module") or "").strip().lower(),
        str(payload.get("source") or "").strip().lower(),
        str(metadata.get("issue_type") or "").strip().lower(),
        str(gap.get("domain") or "").strip().lower(),
        str(module_proposal.get("title") or "").strip().lower(),
        str(payload.get("content") or "")[:120].strip().lower(),
    ]
    raw = "|".join(parts)
    return sha256(raw.encode("utf-8")).hexdigest()
