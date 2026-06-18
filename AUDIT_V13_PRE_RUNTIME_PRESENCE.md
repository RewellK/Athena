# AUDIT V13-PRE Runtime Presence

## Objetivo

Implementar a primeira camada de presenca persistente da Athena sem transforma-la em wrapper de LLM, GUI ou sistema de automodificacao.

## Implementado

- `runtime/` com supervisor, estado, store, event bus, scheduler, loop, task registry, audit log, shutdown seguro, status e briefing.
- `commands/` com palheta de comandos, modos e interpretador local.
- `learning/` com sessao supervisionada, candidatos, harvest worker, review queue, promotion engine, buffer diario, estudo diario e relatorio.
- Integracao no `Athena.chat()` para registrar experiencia temporaria no buffer e na sessao ativa.
- Rotas locais no `CognitiveControlEngine` para comandos/status sem LLM.

## Garantias

- `Athena.chat()` continua funcionando com runtime offline.
- Comandos de status, diagnostico, aprendizagem e estudo usam orgaos locais.
- Candidatos nao viram memoria confirmada automaticamente.
- Aprovacao nao significa promocao irreversivel.
- LLMTeacher continua opcional e auxiliar.
- Buffer diario e runtime state ficam em `logs/`, fora do versionamento.

## Nao Implementado De Proposito

- voz continua;
- wake word;
- reconhecimento de voz;
- ambient listening;
- speaker authentication;
- Git write;
- auto-commit;
- push;
- merge;
- scaffold automatico de orgaos;
- instalacao de dependencias.

## Testes

Cobertura adicionada em `tests/test_v13_pre_runtime_presence.py`.

Cobre:

- start/pause/resume/run_once do runtime;
- falha de worker capturada;
- modo aprendizagem;
- candidatos sem memoria confirmada automatica;
- aprovacao/edicao/rejeicao/consolidacao;
- comando estudar e relatorio local;
- status/diagnostico sem LLM;
- chat funcionando com runtime offline.

## Riscos Restantes

- O `BackgroundCognitionLoop` existe, mas fica desativado por padrao para evitar processamento inesperado.
- Heuristicas locais de candidato sao conservadoras e ainda simples.
- Promocao para alguns destinos futuros ainda e documentada, nao completa.
- A GUI ainda precisa expor esses estados de forma visual em uma etapa posterior.

## Long-term learning persistence

Aprendizados aprovados sao persistidos em `long_term_memory`, no `knowledge.db`.

A tabela `long_term_memory` ganhou `metadata_json` com migracao idempotente via `_ensure_column`. Bancos antigos continuam abrindo; se a coluna nao existir, ela e adicionada sem apagar dados.

Metadata minima gravada:

- `origin`: `supervised_learning_session` ou outra origem supervisionada;
- `session_id`;
- `promoted_at`;
- `approved_by`: `user`;
- `candidate_type`;
- `destination`;
- `confidence`;
- `status`: `confirmed/promoted`;
- `source`: `local_heuristic` ou `llm_teacher`;
- `original_candidate_id`;
- `original_text`.

Prova automatizada:

- `tests/test_v13_pre_long_term_learning_persistence.py` cria Athena com banco temporario persistente;
- inicia runtime;
- ativa aprendizagem;
- cria candidatos;
- aprova um e rejeita outro;
- consolida somente aprovado;
- valida metadata em `long_term_memory`;
- desliga runtime;
- fecha conexao;
- recria Athena com o mesmo banco;
- descarta buffer diario e candidatos;
- simula +7 dias alterando `created_at/promoted_at`;
- consulta via `Athena.chat()`;
- valida `llm_calls == 0`.

Isso prova que a resposta nao vem de RAM, `ConversationContext`, `DayMemoryBuffer`, `LearningCandidateStore`, sessao ativa nem LLM.

Rejeitados nao viram memoria confirmada: o teste pergunta sobre o candidato rejeitado depois do restart e valida que Athena nao o trata como aprendizado local consolidado.

Risco restante: a busca conceitual local ainda e simples. Ela funciona para termos de memoria/aprendizado e deve evoluir para um indice semantico local mais robusto.

## Generalidade e hardcode

A V13-pre nao adiciona hardcode cognitivo de pessoas, relacoes pessoais ou fatos especificos.

Exemplos usados nos testes e transcript, como regras sobre buffer diario e memoria permanente, ficam em `tests/` e scripts manuais. A logica de producao trabalha com classes genericas:

- comandos cognitivos;
- perguntas explicitas;
- sessoes de aprendizagem;
- candidatos;
- politicas de memoria;
- regras de arquitetura;
- propostas de modulo;
- sensibilidade;
- destinos persistentes.

As listas de frases em `CommandInterpreter` sao gramática de comando, nao conhecimento cognitivo. Elas ativam modos como `aprendizagem`, `status`, `diagnostico`, `silencio`, `estudo` e `runtime`.

O `LearningHarvestWorker` usa termos genericos para filtrar ruido e classificar candidatos. Perguntas, status e comandos nao viram candidatos de aprendizado. Isso evita que o estudo diario memorize a propria interface em vez de aprender conteudo relevante.

Ainda existem hardcodes legados de testes V12 com nomes como Fernanda/Francisco/Rewell, mas eles nao foram introduzidos pela V13-pre e permanecem fora da nova logica de runtime/learning persistence.

## Readiness

A V13-pre esta pronta como base de presenca, nao como V13 final.

Ela prepara:

- voz continua, porque agora ha runtime e safe shutdown;
- meeting mode, porque ja existe modo, buffer e revisao;
- daily companion, porque ha estudo do dia e briefing;
- Version X, porque aprendizado aprovado sobrevive a restart e dias simulados.
