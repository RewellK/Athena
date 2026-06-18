# LearningCandidateStore

`LearningCandidateStore` guarda aprendizados candidatos separados de memoria confirmada.

Um candidato representa:

- conteudo observado;
- motivo;
- tipo;
- destino sugerido;
- risco;
- status;
- historico de edicao;
- exigencia de revisao humana.

Status:

- `candidate`
- `approved`
- `rejected`
- `edited`
- `promoted`
- `discarded`
- `rejected_by_policy`

## Candidate != Confirmed

Criar candidato nao altera World Model nem memoria permanente.

`approved` significa que Rewell aceitou a hipotese. Ainda assim, a consolidacao precisa de destino claro.

`promoted` significa que a Athena conseguiu enviar o candidato aprovado para um destino local disponivel.

## Persistencia

Quando um candidato aprovado e promovido para `long_term_memory`, a memoria recebe metadata:

- `origin`
- `session_id`
- `promoted_at`
- `approved_by`
- `candidate_type`
- `destination`
- `confidence`
- `status`
- `source`
- `original_candidate_id`
- `original_text`

Candidatos rejeitados nao sao promovidos.
