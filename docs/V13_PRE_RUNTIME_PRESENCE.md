# V13-pre Runtime Presence

A V13-pre cria a primeira presenca temporal da Athena.

Ela nao e Jarvis completo. Ela e a base para a Athena permanecer, observar, estudar, separar candidatos, aguardar aprovacao e lembrar depois.

## Ciclo provado

1. Runtime inicia e entra em `idle`.
2. Rewell ativa `comando aprendizagem`.
3. Conversas entram no `DayMemoryBuffer` e na sessao ativa.
4. `RuntimeSupervisor.run_once()` aciona workers leves.
5. `LearningHarvestWorker` cria candidatos.
6. Athena mostra relatorio.
7. Rewell edita, aprova e rejeita candidatos.
8. Apenas aprovados sao consolidados.
9. Runtime desliga com safe shutdown.
10. Athena reabre com o mesmo `knowledge.db`.
11. Buffer/candidatos podem ser descartados.
12. Dias simulados depois, Athena recupera a regra localmente sem LLM.
