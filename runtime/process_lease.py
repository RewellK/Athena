"""Cooperative process ownership for the supported desktop/CLI/resident entrypoints."""
import contextlib
import fcntl
import os
from pathlib import Path


@contextlib.contextmanager
def lease(path, blocking=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    acquired = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            acquired = True
        except BlockingIOError:
            pass
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def foreground_active(directory="logs"):
    with lease(Path(directory) / "foreground.lock", blocking=False) as acquired:
        return not acquired


@contextlib.contextmanager
def foreground_session(directory="logs"):
    # Foreground request persists until exit, causing resident to release core.
    with lease(Path(directory) / "foreground.lock", blocking=False) as requested:
        if not requested:
            raise RuntimeError("Athena já está aberta em outro terminal ou janela.")
        with lease(Path(directory) / "core.lock"):
            yield


def close_core(athena):
    presence=getattr(athena,'foreground_presence',None)
    if presence:
        presence.stop()
    athena.runtime_supervisor.stop(reason="process_handoff")
    runner = getattr(athena, "background_task_runner", None)
    if runner:
        runner.shutdown()
    agent_runtime = getattr(athena, 'agent_runtime', None)
    if agent_runtime:
        agent_runtime.close()
    athena.memory.close()
