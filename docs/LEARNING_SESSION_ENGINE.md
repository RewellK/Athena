# LearningSessionEngine

`LearningSessionEngine` controla sessoes explicitas de aprendizado supervisionado.

O comando `Athena, aprender.` cria uma sessao `active` com escopo inicial `current_conversation`.

Uma sessao registra mensagens e contadores, mas nao salva memoria confirmada.

Campos principais:

- `id`
- `status`
- `started_at`
- `ended_at`
- `scope`
- `source`
- `use_llm_teacher`
- `requires_review`
- `created_candidates_count`
- `approved_count`
- `rejected_count`

## Contrato

Sessao ativa significa observacao estruturada, nao memorizacao permanente.

O runtime pode chamar `LearningHarvestWorker` para transformar mensagens da sessao em `LearningCandidate`.

`LLMTeacher` pode sugerir classificacao quando habilitada, mas nao confirma nada sozinha.
