import time
import traceback


class WorkerScheduler:
    def __init__(self, event_bus=None, task_registry=None, logger=None):
        self.event_bus = event_bus
        self.task_registry = task_registry
        self.logger = logger
        self._workers = {}
        self._last_run = {}
        self.failure_count = 0

    def register(self, name, worker, min_interval_seconds=0, allow_safe_mode=False):
        self._workers[name] = {
            "worker": worker,
            "min_interval_seconds": float(min_interval_seconds or 0),
            "allow_safe_mode": bool(allow_safe_mode),
        }
        return name

    def run_once(self, paused=False, safe_mode=False):
        if paused:
            return {"status": "paused", "workers_run": 0, "workers_failed": 0}
        workers_run = 0
        workers_failed = 0
        for name, spec in list(self._workers.items()):
            if safe_mode and not spec.get("allow_safe_mode"):
                continue
            now = time.time()
            last = self._last_run.get(name, 0)
            if now - last < spec.get("min_interval_seconds", 0):
                continue
            self._last_run[name] = now
            worker = spec.get("worker")
            try:
                self._publish("worker_started", {"worker": name})
                if hasattr(worker, "run_once"):
                    result = worker.run_once()
                elif callable(worker):
                    result = worker()
                else:
                    result = {"status": "skipped", "reason": "worker_not_callable"}
                workers_run += 1
                self._publish("worker_completed", {"worker": name, "result": result or {}})
            except Exception as error:
                workers_failed += 1
                self.failure_count += 1
                if self.logger and hasattr(self.logger, "log_exception"):
                    self.logger.log_exception("RUNTIME_WORKER_FAILED", error, {"worker": name})
                elif self.logger and hasattr(self.logger, "log"):
                    self.logger.log("RUNTIME_WORKER_FAILED", f"{name}: {error}")
                self._publish(
                    "worker_failed",
                    {"worker": name, "error": str(error), "traceback": traceback.format_exc()},
                )
        return {"status": "completed", "workers_run": workers_run, "workers_failed": workers_failed}

    def _publish(self, event_type, payload):
        if self.event_bus:
            self.event_bus.publish(event_type, payload)
