import threading
import time


class BackgroundCognitionLoop:
    def __init__(self, supervisor=None, interval_seconds=5.0):
        self.supervisor = supervisor
        self.interval_seconds = float(interval_seconds or 5.0)
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="athena-runtime-loop")
        self._thread.start()
        return True

    def stop(self, timeout=2.0):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        return True

    def run_once(self):
        if not self.supervisor:
            return {"status": "missing_supervisor"}
        return self.supervisor.run_once(from_loop=True)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self.run_once()
            finally:
                self._stop_event.wait(self.interval_seconds)
