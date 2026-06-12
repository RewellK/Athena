import json
import os
import threading
import time
from datetime import datetime


class ConversationMetrics:
    """Records route-level performance without affecting cognition."""

    def __init__(self, path="logs/conversation_metrics.jsonl", logger=None):
        self.path = path
        self.logger = logger
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def start(self):
        return time.perf_counter()

    def finish(self, started_at, input_text, metadata):
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        payload = dict(metadata or {})
        payload["response_llm_calls"] = payload.get("response_llm_calls", payload.get("natural_response_llm_calls", 0))
        payload.update({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "input": self._clip(input_text),
            "duration_ms": duration_ms,
            "total_ms": duration_ms,
            "total_duration_ms": duration_ms,
        })
        try:
            with self._lock:
                with open(self.path, "a", encoding="utf-8") as file:
                    file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            if self.logger:
                self.logger.log("CONVERSATION_METRICS", json.dumps(payload, ensure_ascii=False))
        except Exception as error:
            if self.logger:
                self.logger.log("CONVERSATION_METRICS_ERROR", str(error))
        return payload

    def _clip(self, text, limit=300):
        text = str(text or "")
        return text if len(text) <= limit else text[:limit] + "..."
