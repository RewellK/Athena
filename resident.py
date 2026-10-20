"""Local resident: no listener or shell. Inference only for explicitly queued goals."""
import argparse
import os
from pathlib import Path
import signal
import threading
import time

from runtime.process_lease import close_core, foreground_active, lease

from desktop.paths import data_home
ROOT = data_home()


def run(once=False, interval=30):
    from brain.orchestrator import Athena
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    with lease(ROOT / "logs/resident.lock", blocking=False) as single:
        if not single:
            raise RuntimeError("Serviço Athena já está ativo.")
        while not stop.is_set():
            if foreground_active():
                if once:
                    return
                stop.wait(.5)
                continue
            with lease(ROOT / "logs/core.lock", blocking=False) as acquired:
                if not acquired:
                    if once:
                        return
                    stop.wait(.5)
                    continue
                athena = Athena()
                watch_stop=threading.Event()
                def watch_handoff():
                    while not watch_stop.wait(.2):
                        if stop.is_set() or foreground_active():
                            athena.cancel_current_turn(reason='shutdown' if stop.is_set() else 'foreground_handoff')
                watcher=threading.Thread(target=watch_handoff,daemon=True,name='athena-handoff')
                watcher.start()
                try:
                    # Overrides are in-memory only. No computer/browser/external tools
                    # or teacher; queued goals may use local inference within limits.
                    queued_model=athena.settings.get('queuedGoalModelEnabled',athena.settings.get('useLLM',True))
                    athena.settings.values.update(useLLM=False, voiceEnabled=False,
                        queuedGoalModelEnabled=queued_model,
                        messageReceivedSoundEnabled=False,
                        autoExecuteActions=False, humanApprovalRequired=True,
                        autoLearnPermanentKnowledge=False, allowExternalRequests=False,
                        asyncLlmTeacherEnabled=False, runtimeBackgroundLoopEnabled=False,
                        computerToolsEnabled=False, browserToolsEnabled=False)
                    was_paused = athena.runtime_supervisor.get_status().get("paused")
                    athena.runtime_supervisor.start(background=False)
                    if was_paused:
                        athena.runtime_supervisor.pause(reason="restored_pause")
                    if not once:
                        athena.start_foreground_presence()
                    next_cycle = 0
                    while not stop.is_set() and not foreground_active():
                        if time.monotonic() >= next_cycle:
                            athena.runtime_supervisor.run_once()
                            if once and athena.settings.get('agentBackend','legacy')=='openjarvis':
                                athena.agent_maintenance()
                            next_cycle = time.monotonic() + max(5, interval)
                        if once:
                            return
                        stop.wait(.5)
                finally:
                    watch_stop.set()
                    watcher.join(timeout=1)
                    close_core(athena)
            if once:
                return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Presença local supervisionada da Athena")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=30)
    args = parser.parse_args()
    os.chdir(ROOT)
    os.umask(0o077)
    run(args.once, args.interval)
