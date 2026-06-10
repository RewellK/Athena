import json
import os
import traceback
from datetime import datetime

from error_awareness.error_analyzer import ErrorAnalyzer


class ErrorCapture:
    """Captures exceptions, writes technical logs and stores the last analyzed error."""

    def __init__(self, logger=None, path="logs/last_error.json"):
        self.logger = logger
        self.path = path
        self.analyzer = ErrorAnalyzer()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def capture(self, error, context=None):
        context = context or {}
        stacktrace = traceback.format_exc()
        analysis = self.analyzer.analyze(error, stacktrace, context)
        payload = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "error_type": type(error).__name__,
            "error": str(error),
            "context": context,
            "analysis": analysis,
            "stacktrace": stacktrace,
        }
        if self.logger:
            self.logger.log_exception("ATHENA_ERROR_CAPTURED", error, context)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)
        return payload

    def last_error(self):
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as error:
            if self.logger:
                self.logger.log_exception("LAST_ERROR_READ_FAILED", error, {"module": "error_awareness/error_capture.py"})
            return None
