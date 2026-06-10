import queue
import threading
import traceback


class BackgroundTaskRunner:
    """Single-worker background queue for GUI tasks.

    A single worker keeps SQLite access serialized at the application level,
    while MemoryDB also protects the database with its own lock.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._run, daemon=True, name="athena-background-worker")
        self._worker.start()

    def submit(self, fn, on_success=None, on_error=None, description="background_task"):
        self._queue.put((fn, on_success, on_error, description))

    def _run(self):
        while True:
            fn, on_success, on_error, description = self._queue.get()
            try:
                result = fn()
                if on_success:
                    on_success(result)
            except Exception as error:
                if self.logger:
                    self.logger.log_exception("BACKGROUND_TASK_ERROR", error, {"description": description})
                if on_error:
                    on_error(error, traceback.format_exc())
            finally:
                self._queue.task_done()
