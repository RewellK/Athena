from datetime import datetime


class SafeShutdownManager:
    def __init__(self, state_store=None, event_bus=None):
        self.state_store = state_store
        self.event_bus = event_bus

    def shutdown(self, reason="manual_shutdown"):
        if self.event_bus:
            self.event_bus.publish("runtime_stopping", {"reason": reason})
        if self.state_store:
            self.state_store.set_state("shutting_down", reason=reason)
            self.state_store.update(last_shutdown_at=datetime.now().isoformat(timespec="seconds"))
            self.state_store.set_state("stopped", reason=reason)
        if self.event_bus:
            self.event_bus.publish("runtime_stopped", {"reason": reason})
        return {"status": "stopped", "reason": reason}
