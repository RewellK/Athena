import os
import traceback
import threading
from datetime import datetime


class AthenaLogger:
    """Small thread-safe logger used by terminal, GUI and background tasks."""

    def __init__(self, log_path="logs/athena.log"):
        self.log_path = log_path
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log(self, category, message):
        created_at = datetime.now().isoformat(timespec="seconds")
        line = f"[{created_at}] [{category}] {message}\n"
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as file:
                file.write(line)

    def log_exception(self, category, error, context=None):
        context = context or {}
        created_at = datetime.now().isoformat(timespec="seconds")
        details = {
            "timestamp": created_at,
            "category": category,
            "error_type": type(error).__name__,
            "error": str(error),
            "context": context,
            "stacktrace": traceback.format_exc(),
        }
        os.makedirs("logs", exist_ok=True)
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as file:
                file.write(f"[{created_at}] [{category}] {type(error).__name__}: {error} | context={context}\n")
            with open("logs/errors.log", "a", encoding="utf-8") as file:
                file.write(str(details) + "\n")
