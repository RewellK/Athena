# Memória curta, média e longa — refatoração incremental

A migração é aditiva sobre `knowledge.db`; não apaga o banco nem reconstrói os fatos existentes. Os contratos de listagem continuam retornando as mesmas colunas para manter GUI e órgãos compatíveis.

## Responsabilidades

| Camada | Conteúdo e duração | O que não significa |
|---|---|---|
| Contexto recente | Até 40 mensagens, TTL configurável (24 h por padrão), tabela própria | Não é conhecimento confirmado |
| Curta | Observações candidatas, importância, contagem de observações, prazo por `shortTermMemoryHours` | Repetição não prova verdade |
| Média | Conteúdo em acompanhamento, TTL por `midTermMemoryDays`, vínculos com origem curta | Não substitui o World Model nem vira fato por frequência de palavras |
| Longa | Conteúdo consolidado por revisão/política explícita, sem TTL automático | Não aprende habilidade executável só por conter instruções |
| Memória procedural | Receitas do SkillBackend e exemplos/padrões linguísticos revisados | Não é ajuste dos pesos da LLM |

## Mudanças implementadas

- Reobservar o mesmo conteúdo curto atualiza o prazo, relevância máxima e `seen_count`, mantendo um único registro. A data original é preservada e `last_seen_at` registra recorrência. Não confunde variações semanticamente parecidas como duplicatas: a chave é o hash normalizado existente.
- A memória média também atualiza prazo e contagem máxima ao reencontrar o mesmo resumo; não cria duplicatas.
- A consolidação curta → média preserva o conteúdo original. O algoritmo antigo que promovia palavras frequentes para frases como “termo apareceu N vezes” foi retirado desse caminho. Agora a promoção depende de observações repetidas do conteúdo ou importância suficiente, e grava vínculo em `memory_evidence`.
- `source_count` dessa consolidação representa número de observações, não fontes independentes nem comprovação factual.
- A expiração curta/média arquiva os registros (`archived=1`) e os oculta das consultas ativas; não os apaga. A lista com `include_expired=True` permite revisão histórica. Nenhum fato longo confirmado é removido por esse ciclo.
- Promoção média → longa exige que a origem exista e registra ID intermediário, responsável, motivo e data. O fluxo de aprendizagem supervisionada anterior continua usando sua metadata própria e não foi substituído.
- Busca local FTS5 sobre as três camadas, com atualização por triggers SQLite. A migração indexa o banco preexistente uma vez. Consulta filtra prazo/arquivo e identifica explicitamente contexto candidato versus longo consolidado.
- Builds sem FTS5 usam uma busca lexical alternativa. Não exige embeddings nem LLM. A recuperação é textual, não compreensão semântica geral.
- `ContextBuilder` recebe memórias recuperadas relevantes e rotula as temporárias como candidatas. Os relatórios históricos e APIs existentes continuam disponíveis.
- O residente executa manutenção a cada cinco minutos quando não pausado/modo seguro; não chama LLM para expirar ou consolidar observações em memória de trabalho.

## Migração e verificação

Os testes criam um banco no formato antigo, migram duas vezes e verificam que os dados longos continuam presentes e o índice não duplica registros. Também verificam deduplicação, repetição, origem da promoção, expiração sem exclusão, busca sem retornar candidatos expirados e preservação da memória longa.

Faça backup antes de migrar. A tabela de contexto recente elimina registros vencidos por sua política própria de memória de trabalho; esse comportamento é diferente do arquivamento das observações curta/média. Logs, buffers diários e outros stores ainda têm políticas próprias.

## Limites

Não há resolução automática confiável de contradições, esquecimento equivalente ao humano, embeddings semânticos ou reconsolidação geral. A busca por relevância textual pode recuperar um candidato errado; o rótulo de origem/confirmação é parte da avaliação do Core. Armazenamento arquivado pode crescer e precisa de revisão/backup. Purga definitiva não é automática. O prazo de uma camada não apaga cópias em outros stores/logs/backups.
