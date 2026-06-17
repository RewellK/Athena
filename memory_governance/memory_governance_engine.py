import json
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class MemoryGovernanceRecord:
    memory_id: str
    content: str
    memory_type: str
    status: str
    confidence: float = 0.5
    relevance_score: int = 0
    emotional_score: int = 0
    source: str = "memory"
    source_message: str = ""
    evidence_ids: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    last_accessed_at: str = ""
    access_count: int = 0
    ttl: str = ""
    promoted_from: str = ""
    related_entities: list = field(default_factory=list)
    related_reflections: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class MemoryGovernanceEngine:
    """Read-only governance view over Athena memory layers.

    Cleanup is advisory. This engine marks and reports; it does not delete user
    memories automatically.
    """

    def __init__(self, memory=None, freshness_engine=None):
        self.memory = memory
        self.freshness_engine = freshness_engine

    def snapshot(self):
        return {
            "counts": {
                "raw_conversation": self._safe("count_memories", 0),
                "working_memory": len(self._safe("list_short_term_memory", [], include_expired=False)),
                "short_term_candidate": len(self._safe("list_short_term_memory", [], include_expired=True, processed=False)),
                "long_term_consolidated_memory": self._safe("count_real_long_term_memory", 0),
                "world_model_fact": self._safe("count_world_relationships", 0) + self._safe("count_entity_states", 0),
                "semantic_memory": len(self._safe("list_definitions", [])),
                "episodic_memory": self._safe("count_world_events", 0),
                "relationship_memory": self._safe("count_world_relationships", 0),
                "self_improvement_memory": 0,
                "evidence_memory": 0,
            },
            "pending": self.pending_memories(limit=20),
            "important": self.important_memories(limit=20),
            "cleanup_suggestions": self.cleanup_suggestions(),
        }

    def pending_memories(self, limit=20):
        records = []
        for row in self._safe("list_short_term_memory", [], include_expired=True, processed=False)[:limit]:
            memory_id, content, _hash, created_at, expires_at, score, processed = row
            status = "candidate" if not processed else "extracted"
            if self._is_expired(expires_at):
                status = "stale"
            records.append(MemoryGovernanceRecord(
                memory_id=f"short_term:{memory_id}",
                content=content,
                memory_type="short_term_candidate",
                status=status,
                confidence=0.55,
                relevance_score=int(score or 0),
                source="short_term_memory",
                created_at=created_at,
                updated_at=created_at,
                ttl=expires_at,
            ).to_dict())
        pending_relevance = [
            row for row in self._safe("list_memory_relevance", [], confirmation_required=True)
            if not row[14]
        ]
        for row in pending_relevance[:limit]:
            records.append(self._relevance_record(row, status="pending_confirmation"))
        return records[:limit]

    def important_memories(self, limit=20):
        records = []
        high_relevance = [
            row for row in self._safe("list_memory_relevance", [])
            if int(row[5] or 0) >= 70
        ]
        for row in high_relevance[:limit]:
            records.append(self._relevance_record(row, status="confirmed" if row[14] else "candidate"))
        for row in self._safe("list_long_term_memory", [])[:limit]:
            memory_id, content, source, importance, created_at = row
            records.append(MemoryGovernanceRecord(
                memory_id=f"long_term:{memory_id}",
                content=content,
                memory_type="long_term_consolidated_memory",
                status="consolidated",
                confidence=0.8,
                relevance_score=int(importance or 0),
                source=source,
                created_at=created_at,
                updated_at=created_at,
            ).to_dict())
        return records[:limit]

    def cleanup_suggestions(self):
        suggestions = []
        expired_short = [
            row for row in self._safe("list_short_term_memory", [], include_expired=True)
            if self._is_expired(row[4]) and not row[6]
        ]
        if expired_short:
            suggestions.append({
                "issue_type": "memory_stale_detected",
                "count": len(expired_short),
                "suggestion": "Arquivar ou revisar candidatos de memória curta expirados antes de apagar.",
                "requires_human_review": True,
            })
        duplicates = self._duplicate_long_term()
        if duplicates:
            suggestions.append({
                "issue_type": "memory_duplication_detected",
                "count": len(duplicates),
                "suggestion": "Consolidar duplicatas por conteúdo normalizado, mantendo origem e data.",
                "requires_human_review": True,
            })
        return suggestions

    def _duplicate_long_term(self):
        seen = {}
        duplicates = []
        for row in self._safe("list_long_term_memory", []):
            marker = " ".join(str(row[1] or "").strip().lower().split())
            if marker in seen:
                duplicates.append(row)
            else:
                seen[marker] = row
        return duplicates

    def _relevance_record(self, row, status):
        (
            memory_id, layer, layer_id, content, source_message, relevance_score, _importance_score,
            emotional_score, _relationship_score, _identity_score, _future_score, priority,
            related_entities_json, confirmation_required, confirmed, _follow_up_question, reason, created_at,
        ) = row
        related_entities = []
        try:
            related_entities = json.loads(related_entities_json or "[]")
        except json.JSONDecodeError:
            related_entities = []
        if confirmation_required and not confirmed:
            status = "pending_confirmation"
        return MemoryGovernanceRecord(
            memory_id=f"relevance:{memory_id}",
            content=content,
            memory_type=str(layer or "memory_relevance"),
            status=status,
            confidence=0.7 if confirmed else 0.5,
            relevance_score=int(relevance_score or 0),
            emotional_score=int(emotional_score or 0),
            source="memory_relevance",
            source_message=source_message or "",
            created_at=created_at,
            updated_at=created_at,
            related_entities=related_entities,
            promoted_from=str(layer_id or ""),
        ).to_dict()

    def _is_expired(self, value):
        try:
            return datetime.fromisoformat(str(value)) <= datetime.now()
        except (TypeError, ValueError):
            return False

    def _safe(self, method_name, fallback, *args, **kwargs):
        if not self.memory or not hasattr(self.memory, method_name):
            return fallback
        try:
            return getattr(self.memory, method_name)(*args, **kwargs)
        except Exception:
            return fallback
