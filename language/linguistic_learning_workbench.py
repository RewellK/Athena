import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class TrainingExample:
    utterance: str
    expected_intent: str
    expected_target: str = ""
    expected_subject: str = ""
    expected_verb: str = ""
    expected_object: str = ""
    expected_relation_type: str = ""
    expected_owner: str = ""
    expected_scope: str = ""
    expected_domain: str = ""
    expected_frame: dict = field(default_factory=dict)
    actual_frame: dict = field(default_factory=dict)
    correction: str = ""
    context: dict = field(default_factory=dict)
    source: str = "human_approved"
    confidence: float = 1.0
    status: str = "candidate"
    requires_human_review: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    validated_at: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        return cls(**clean)


@dataclass
class SemanticPattern:
    name: str
    intent: str
    match_text: str
    relation_type: str = ""
    target_source: str = "utterance"
    examples: list = field(default_factory=list)
    frame_template: dict = field(default_factory=dict)
    confidence: float = 0.7
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    status: str = "candidate"
    source_example_id: str = ""
    requires_human_review: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in payload.items() if key in known}
        if not clean.get("name"):
            clean["name"] = str(clean.get("intent") or "semantic_pattern")
        return cls(**clean)


class LinguisticLearningWorkbench:
    """Stores linguistic examples and promotes validated examples to patterns."""

    def __init__(self, path=None):
        self.path = path
        self._lock = threading.RLock()
        self._examples = []
        self._patterns = []
        self._load()

    def save_example(self, example):
        example = example if isinstance(example, TrainingExample) else TrainingExample.from_dict(example)
        with self._lock:
            self._examples.append(example)
            self._save()
        return example.to_dict()

    def examples_by_intent(self, intent):
        with self._lock:
            items = [example for example in self._examples if example.expected_intent == intent]
        return [item.to_dict() for item in items]

    def list_examples(self, status=None):
        with self._lock:
            items = list(self._examples)
        if status:
            items = [item for item in items if item.status == status]
        return [item.to_dict() for item in items]

    def list_patterns(self, status=None):
        with self._lock:
            items = list(self._patterns)
        if status:
            items = [item for item in items if item.status == status]
        return [item.to_dict() for item in items]

    def example_from_reflection_event(self, event):
        event = event.to_dict() if hasattr(event, "to_dict") else dict(event or {})
        issue_type = event.get("issue_type", "reflection_issue")
        utterance = event.get("source_message", "")
        expected_intent = self._intent_from_issue(issue_type)
        return self.save_example(TrainingExample(
            utterance=utterance,
            expected_intent=expected_intent,
            source="reflection_event",
            confidence=0.4,
            status="candidate",
            requires_human_review=True,
            context={"issue_type": issue_type, "suggested_tests": event.get("suggested_tests", [])},
        ))

    def candidate_from_llm_suggestion(self, utterance, suggestion):
        suggestion = dict(suggestion or {})
        return self.save_example(TrainingExample(
            utterance=utterance,
            expected_intent=suggestion.get("intent", "unknown"),
            expected_target=suggestion.get("target", ""),
            expected_subject=suggestion.get("subject", ""),
            expected_verb=suggestion.get("verb", ""),
            expected_object=suggestion.get("object", ""),
            expected_relation_type=suggestion.get("relation_type", ""),
            expected_owner=suggestion.get("owner", ""),
            expected_scope=suggestion.get("scope", ""),
            expected_domain=suggestion.get("domain", ""),
            source="llm_suggestion",
            confidence=float(suggestion.get("confidence", 0.35) or 0.35),
            status="candidate",
            requires_human_review=True,
        ))

    def validate_example_as_pattern(self, example_id):
        with self._lock:
            example = next((item for item in self._examples if item.id == example_id), None)
            if not example:
                return None
            example.status = "converted_to_pattern"
            example.requires_human_review = False
            example.validated_at = datetime.now().isoformat(timespec="seconds")
            pattern = SemanticPattern(
                name=self._pattern_name(example),
                intent=example.expected_intent,
                match_text=self._pattern_text(example),
                relation_type=example.expected_relation_type,
                examples=[example.utterance],
                frame_template=example.expected_frame or self._frame_template(example),
                confidence=max(0.5, float(example.confidence or 0.5)),
                status="confirmed",
                source_example_id=example.id,
                requires_human_review=False,
            )
            self._patterns.append(pattern)
            self._save()
            return pattern.to_dict()

    def reject_example(self, example_id, reason=""):
        with self._lock:
            example = next((item for item in self._examples if item.id == example_id), None)
            if not example:
                return None
            example.status = "rejected"
            example.correction = reason or example.correction
            example.requires_human_review = False
            example.validated_at = datetime.now().isoformat(timespec="seconds")
            self._save()
            return example.to_dict()

    def confirmed_patterns(self):
        with self._lock:
            patterns = [item for item in self._patterns if item.status == "confirmed"]
        return [item.to_dict() for item in patterns]

    def _pattern_text(self, example):
        value = example.expected_object or example.expected_target or example.utterance
        return " ".join(str(value or "").strip().lower().split())

    def _pattern_name(self, example):
        base = f"{example.expected_intent}_{example.expected_relation_type or example.expected_scope or 'pattern'}"
        return "_".join(part for part in base.lower().replace("-", "_").split("_") if part)

    def _frame_template(self, example):
        return {
            "intent": example.expected_intent,
            "target": example.expected_target,
            "subject": example.expected_subject,
            "verb": example.expected_verb,
            "object": example.expected_object,
            "relation_type": example.expected_relation_type,
            "owner": example.expected_owner,
            "scope": example.expected_scope,
            "domain": example.expected_domain,
        }

    def _intent_from_issue(self, issue_type):
        return {
            "missing_pronoun_resolution": "entity_query",
            "recent_entity_resolution_failed": "entity_query",
            "unknown_loop": "unknown_recovery",
            "research_strategy_missing": "external_information",
        }.get(issue_type, "unknown")

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        self._examples = [TrainingExample.from_dict(item) for item in payload.get("examples", [])]
        self._patterns = [SemanticPattern.from_dict(item) for item in payload.get("patterns", [])]

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {
            "examples": [item.to_dict() for item in self._examples],
            "patterns": [item.to_dict() for item in self._patterns],
        }
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
