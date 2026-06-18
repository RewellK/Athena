# Runtime Presence Kernel

A V13-pre adiciona o primeiro corpo temporal da Athena.

O runtime nao substitui `Athena.chat()`. Ele existe ao lado do chat para manter estado, heartbeat, filas leves, auditoria e status local.

## Orgaos

- `RuntimeSupervisor`: inicia, pausa, retoma, encerra, registra heartbeat e coordena workers.
- `RuntimeStateStore`: persiste estado simples em JSON local.
- `RuntimeEventBus`: publica eventos sem acoplar workers ao supervisor.
- `PendingTaskRegistry`: organiza tarefas internas e deduplica pendencias obvias.
- `WorkerScheduler`: roda workers pequenos, captura falhas e respeita pausa/safe mode.
- `BackgroundCognitionLoop`: ciclo opcional controlado; desativado por padrao.
- `CognitiveStatusEngine`: responde status local sem LLM.
- `DailyBriefingPlanner`: prepara resumo local de pendencias.

## Limites

O runtime nao implementa voz continua, wake word, microfone sempre ligado, automodificacao, Git write, push, merge ou instalacao de dependencias.

Workers nao devem promover memoria, usar fontes externas ou executar acoes perigosas sem aprovacao humana.

## Estados

Estados minimos implementados:

- `offline`
- `starting`
- `idle`
- `awake`
- `processing`
- `reflecting`
- `consolidating_memory`
- `reviewing_learning`
- `awaiting_approval`
- `safe_mode`
- `shutting_down`
- `stopped`

Cada estado tem descricao, permissao e restricao. `safe_mode` limita operacoes a leitura/localidade segura.
