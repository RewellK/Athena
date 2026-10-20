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
        self._closed = False
        self._worker = threading.Thread(target=self._run, daemon=True, name="athena-background-worker")
        self._worker.start()

    def submit(self, fn, on_success=None, on_error=None, description="background_task"):
        if self._closed:
            raise RuntimeError("Background worker encerrado")
        self._queue.put((fn, on_success, on_error, description))

    def _run(self):
        while True:
            task = self._queue.get()
            if task is None:
                self._queue.task_done()
                return
            fn, on_success, on_error, description = task
            try:
                result = fn()
                if on_success and not self._closed:
                    on_success(result)
            except Exception as error:
                if self.logger:
                    self.logger.log_exception("BACKGROUND_TASK_ERROR", error, {"description": description})
                if on_error and not self._closed:
                    on_error(error, traceback.format_exc())
            finally:
                self._queue.task_done()

    def shutdown(self):
        if not self._closed:
            self._closed = True
            self._queue.put(None)
        if threading.current_thread() is not self._worker:
            self._worker.join()
