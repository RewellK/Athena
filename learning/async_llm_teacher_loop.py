import json
import os
import queue
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class LlmTeacherInsight:
    turn_id: str
    issue_detected: bool = False
    summary: str = ""
    suggested_frame: dict = field(default_factory=dict)
    suggested_pattern: dict = field(default_factory=dict)
    suggested_memory_update: dict = field(default_factory=dict)
    suggested_research_strategy: dict = field(default_factory=dict)
    suggested_learning_strategy: dict = field(default_factory=dict)
    suggested_test: str = ""
    status: str = "candidate"
    source: str = "llm_teacher"
    confidence: float = 0.35
    requires_human_review: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    insight_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self):
        return asdict(self)


class LlmTeacherInsightStore:
    def __init__(self, path=None):
        self.path = path
        self._lock = threading.RLock()
        self._insights = []
        self._load()

    def save(self, insight):
        insight = insight if isinstance(insight, LlmTeacherInsight) else LlmTeacherInsight(**dict(insight or {}))
        payload = insight.to_dict()
        with self._lock:
            self._insights.append(payload)
            self._save()
        return payload

    def list(self, status=None, limit=20):
        with self._lock:
            items = list(self._insights)
        if status:
            items = [item for item in items if item.get("status") == status]
        return list(reversed(items[-int(limit):]))

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return
        self._insights = list(payload.get("insights", [])) if isinstance(payload, dict) else []

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"insights": self._insights}, file, ensure_ascii=False, indent=2)


class AsyncLlmTeacherLoop:
    """Background teacher loop. It produces candidates, never confirmed truth."""

    def __init__(
        self,
        llm_provider=None,
        store=None,
        workbench=None,
        self_insight_engine=None,
        research_learning_engine=None,
        task_runner=None,
        settings=None,
        logger=None,
    ):
        self.llm_provider = llm_provider
        self.store = store or LlmTeacherInsightStore()
        self.workbench = workbench
        self.self_insight_engine = self_insight_engine
        self.research_learning_engine = research_learning_engine
        self.task_runner = task_runner
        self.settings = settings
        self.logger = logger
        self._queue = queue.Queue()

    def enqueue_turn(self, user_message, athena_response, metadata=None):
        turn = {
            "turn_id": uuid.uuid4().hex,
            "user_message": str(user_message or ""),
            "athena_response": str(athena_response or ""),
            "metadata": dict(metadata or {}),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._queue.put(turn)
        if self._setting("asyncLlmTeacherAutoProcess", True) and self.task_runner:
            self.task_runner.submit(self.process_pending_once, description="async_llm_teacher_loop")
        return turn

    def pending_count(self):
        return self._queue.qsize()

    def process_pending_once(self):
        try:
            turn = self._queue.get_nowait()
        except queue.Empty:
            return None
        try:
            insight = self._teach(turn)
            self._apply_candidate_learning(insight)
            return insight
        finally:
            self._queue.task_done()

    def _teach(self, turn):
        if not self.llm_provider or not self._setting("asyncLlmTeacherEnabled", True):
            insight = LlmTeacherInsight(
                turn_id=turn["turn_id"],
                summary="LLMTeacher indisponível ou desativado; nenhum candidato gerado.",
                status="candidate",
                confidence=0.0,
            )
            return self.store.save(insight)

        prompt = self._prompt(turn)
        try:
            timeout = self._setting("asyncLlmTeacherTimeoutSeconds", 12)
            try:
                result = self.llm_provider.generate(prompt, timeout_seconds=timeout)
            except TypeError:
                result = self.llm_provider.generate(prompt)
            parsed = self._parse_json(result.text if result and result.available else "")
            insight = LlmTeacherInsight(
                turn_id=turn["turn_id"],
                issue_detected=bool(parsed.get("issue_detected")),
                summary=str(parsed.get("summary") or ""),
                suggested_frame=parsed.get("suggested_frame") if isinstance(parsed.get("suggested_frame"), dict) else {},
                suggested_pattern=parsed.get("suggested_pattern") if isinstance(parsed.get("suggested_pattern"), dict) else {},
                suggested_memory_update=parsed.get("suggested_memory_update") if isinstance(parsed.get("suggested_memory_update"), dict) else {},
                suggested_research_strategy=parsed.get("suggested_research_strategy") if isinstance(parsed.get("suggested_research_strategy"), dict) else {},
                suggested_learning_strategy=parsed.get("suggested_learning_strategy") if isinstance(parsed.get("suggested_learning_strategy"), dict) else {},
                suggested_test=str(parsed.get("suggested_test") or ""),
                status="candidate",
                confidence=float(parsed.get("confidence", 0.35) or 0.35),
                requires_human_review=True,
            )
            return self.store.save(insight)
        except Exception as error:
            if self.logger:
                self.logger.log("ASYNC_LLM_TEACHER_ERROR", str(error))
            return self.store.save(LlmTeacherInsight(
                turn_id=turn["turn_id"],
                issue_detected=True,
                summary=f"LLMTeacher falhou sem quebrar Athena.chat(): {error}",
                status="candidate",
                confidence=0.0,
                requires_human_review=True,
            ))

    def _apply_candidate_learning(self, insight):
        insight = dict(insight or {})
        frame = insight.get("suggested_frame") or {}
        if self.workbench and frame:
            self.workbench.candidate_from_llm_suggestion(
                utterance=frame.get("raw_text") or frame.get("utterance") or "",
                suggestion={
                    "intent": frame.get("intent", "unknown"),
                    "target": frame.get("target", ""),
                    "subject": frame.get("subject", ""),
                    "verb": frame.get("verb", ""),
                    "object": frame.get("object", ""),
                    "relation_type": frame.get("relation_type", ""),
                    "owner": frame.get("owner", ""),
                    "scope": frame.get("scope", ""),
                    "domain": frame.get("domain", ""),
                    "confidence": insight.get("confidence", 0.35),
                },
            )
        if self.self_insight_engine:
            self.self_insight_engine.create_from_teacher_insight(insight)
            learning_strategy = insight.get("suggested_learning_strategy") or {}
            if learning_strategy:
                self.self_insight_engine.create_learning_to_learn_insight(
                    source="llm_teacher",
                    content=learning_strategy.get("content", "A LLM sugeriu um modo de melhorar meu próprio aprendizado."),
                    suggested_action=learning_strategy.get("suggested_action", ""),
                    suggested_test=learning_strategy.get("suggested_test", insight.get("suggested_test", "")),
                )
        strategy = insight.get("suggested_research_strategy") or {}
        if self.research_learning_engine and strategy.get("domain"):
            self.research_learning_engine.learn_from_llm_suggestion(
                strategy.get("domain"),
                strategy.get("notes") or insight.get("summary"),
                candidate_sources=strategy.get("candidate_sources") or [],
            )

    def _prompt(self, turn):
        return f"""
Você é uma professora LLM auxiliar da Athena.
Retorne SOMENTE JSON válido. Não responda ao usuário.
Sua saída vira hipótese candidata e exigirá revisão humana.
Não declare fatos externos. Não substitua Memory, WorldModel, EvidenceEngine nem SourceRegistry.
Além de avaliar o turno, sugira quando útil como Athena pode aprender melhor a aprender.

Analise o turno:
{json.dumps(turn, ensure_ascii=False, indent=2)}

Schema:
{{
  "issue_detected": false,
  "summary": "",
  "suggested_frame": {{}},
  "suggested_pattern": {{}},
  "suggested_memory_update": {{}},
  "suggested_research_strategy": {{}},
  "suggested_learning_strategy": {{}},
  "suggested_test": "",
  "confidence": 0.0
}}
""".strip()

    def _parse_json(self, text):
        raw = str(text or "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            return {}
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _setting(self, key, default=None):
        if self.settings and hasattr(self.settings, "get"):
            return self.settings.get(key, default)
        return default
