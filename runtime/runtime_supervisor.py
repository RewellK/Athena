from datetime import datetime

from runtime.background_cognition_loop import BackgroundCognitionLoop
from runtime.pending_task_registry import PendingTaskRegistry
from runtime.runtime_audit_log import RuntimeAuditLog
from runtime.runtime_event_bus import RuntimeEventBus
from runtime.runtime_state_store import RuntimeStateStore
from runtime.safe_shutdown_manager import SafeShutdownManager
from runtime.worker_scheduler import WorkerScheduler


class RuntimeSupervisor:
    def __init__(
        self,
        state_store=None,
        event_bus=None,
        task_registry=None,
        scheduler=None,
        audit_log=None,
        settings=None,
        logger=None,
        learning_harvest_worker=None,
        daily_briefing_planner=None,
    ):
        self.settings = settings
        self.logger = logger
        self.audit_log = audit_log or RuntimeAuditLog(self._setting("runtimeAuditLogPath", "logs/runtime_audit.jsonl"))
        self.event_bus = event_bus or RuntimeEventBus(audit_log=self.audit_log)
        self.state_store = state_store or RuntimeStateStore(self._setting("runtimeStateStorePath", "logs/runtime_state.json"))
        self.task_registry = task_registry or PendingTaskRegistry(self._setting("runtimeTaskStorePath", "logs/runtime_tasks.json"))
        self.scheduler = scheduler or WorkerScheduler(self.event_bus, self.task_registry, logger=logger)
        self.shutdown_manager = SafeShutdownManager(self.state_store, self.event_bus)
        self.loop = BackgroundCognitionLoop(self, interval_seconds=self._setting("runtimeLoopIntervalSeconds", 5))
        self.started_at = ""
        self._configure_default_workers(learning_harvest_worker, daily_briefing_planner)

    def start(self, background=None):
        if self.get_status().get("state") not in {"offline", "stopped", "safe_mode"}:
            return self.get_status()
        now = datetime.now().isoformat(timespec="seconds")
        self.started_at = now
        self.state_store.set_state("starting", reason="runtime_start")
        self.state_store.update(session_started_at=now, paused=False, safe_mode=False)
        self.event_bus.publish("runtime_started", {"session_started_at": now})
        self.state_store.set_state("idle", reason="runtime_ready")
        if background is None:
            background = bool(self._setting("runtimeBackgroundLoopEnabled", False))
        if background:
            self.loop.start()
        return self.get_status()

    def pause(self, reason="manual_pause"):
        self.state_store.update(paused=True)
        self.state_store.set_state("idle", reason=reason)
        self.event_bus.publish("runtime_paused", {"reason": reason})
        return self.get_status()

    def resume(self, reason="manual_resume"):
        self.state_store.update(paused=False)
        self.state_store.set_state("awake", reason=reason)
        self.event_bus.publish("runtime_resumed", {"reason": reason})
        return self.get_status()

    def stop(self, reason="manual_stop"):
        self.loop.stop()
        return self.shutdown_manager.shutdown(reason=reason)

    def heartbeat(self):
        heartbeat_at = self.state_store.heartbeat()
        self.event_bus.publish("heartbeat", {"heartbeat_at": heartbeat_at})
        return heartbeat_at

    def run_once(self, from_loop=False):
        status = self.get_status()
        if status.get("state") in {"offline", "stopped"} and not from_loop:
            self.start(background=False)
            status = self.get_status()
        if status.get("paused"):
            self.heartbeat()
            return {"status": "paused"}
        self.state_store.set_state("processing", reason="runtime_cycle")
        self.heartbeat()
        result = self.scheduler.run_once(paused=status.get("paused"), safe_mode=status.get("safe_mode"))
        if result.get("workers_failed", 0) >= 3:
            self.enter_safe_mode("falhas recorrentes de worker")
        elif not self.get_status().get("safe_mode"):
            self.state_store.set_state("idle", reason="runtime_cycle_completed")
        return result

    def get_status(self):
        snapshot = self.state_store.snapshot()
        state = snapshot.get("state") or {}
        return {
            "state": state.get("name", "offline"),
            "state_description": state.get("description", ""),
            "state_reason": state.get("reason", ""),
            "current_task": state.get("current_task", ""),
            "session_started_at": snapshot.get("session_started_at", ""),
            "last_heartbeat_at": snapshot.get("last_heartbeat_at", ""),
            "last_shutdown_at": snapshot.get("last_shutdown_at", ""),
            "last_error": snapshot.get("last_error", ""),
            "paused": bool(snapshot.get("paused")),
            "safe_mode": bool(snapshot.get("safe_mode")),
            "safe_mode_reason": snapshot.get("safe_mode_reason", ""),
            "pending_snapshot": snapshot.get("pending_snapshot") or {},
        }

    def enter_safe_mode(self, reason):
        self.state_store.update(safe_mode=True, safe_mode_reason=str(reason or "safe_mode"))
        self.state_store.set_state("safe_mode", reason=str(reason or "safe_mode"))
        self.event_bus.publish("safe_mode_entered", {"reason": reason})
        return self.get_status()

    def exit_safe_mode(self, reason="manual_recovery"):
        self.state_store.update(safe_mode=False, safe_mode_reason="")
        self.state_store.set_state("idle", reason=reason)
        self.event_bus.publish("safe_mode_exited", {"reason": reason})
        return self.get_status()

    def _configure_default_workers(self, learning_harvest_worker, daily_briefing_planner):
        self.scheduler.register("health_check", lambda: {"status": "ok"}, min_interval_seconds=0, allow_safe_mode=True)
        if learning_harvest_worker:
            self.scheduler.register("learning_harvest", learning_harvest_worker, min_interval_seconds=0)
        if daily_briefing_planner:
            self.scheduler.register("daily_briefing", lambda: daily_briefing_planner.prepare(), min_interval_seconds=60)

    def _setting(self, key, default=None):
        if self.settings and hasattr(self.settings, "get"):
            return self.settings.get(key, default)
        return default
