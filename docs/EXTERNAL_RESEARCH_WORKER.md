# External Research Worker V12.8

## Objetivo

O `AsyncExternalResearchWorker` prepara a Athena para consultar fontes externas sem bloquear a conversa principal.

Nesta fase ele é uma fila local simples, sem thread complexa.

## Job

`ExternalResearchJob` possui:

- `job_id`
- `domain`
- `query`
- `source_id`
- `status`
- `created_at`
- `started_at`
- `completed_at`
- `result`
- `evidence`
- `error`

Status possíveis:

- `pending`
- `running`
- `completed`
- `failed`
- `cancelled`

## Fluxo futuro

Quando houver fonte habilitada e conector validado:

1. Athena cria job.
2. Responde rápido: “Vou pesquisar isso, já te respondo.”
3. Worker processa.
4. `EvidenceEngine` gera evidência.
5. GUI futura pode exibir resultado final quando o job completar.

## Limitação atual

A GUI atual ainda não envia segunda mensagem assíncrona automaticamente.

Por isso a V12.8 entrega:

- estrutura de job;
- fila local;
- processamento manual com `process_pending_once()`;
- testes com conector mock;
- documentação do fluxo assíncrono.

Não há consulta real de internet nesta fase.
