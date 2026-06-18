# RuntimeSupervisor

`RuntimeSupervisor` e o coordenador do corpo temporal da Athena.

Metodos principais:

- `start()`
- `pause()`
- `resume()`
- `stop()`
- `heartbeat()`
- `get_status()`
- `run_once()`
- `enter_safe_mode(reason)`
- `exit_safe_mode()`

`start()` prepara estado e heartbeat.

`run_once()` executa um ciclo curto de workers, sem loop infinito e sem bloquear `Athena.chat()`.

`stop()` usa `SafeShutdownManager` para persistir `last_shutdown_at` e estado final `stopped`.

Falhas de worker sao capturadas pelo `WorkerScheduler`. Falhas recorrentes podem levar a `safe_mode`.
