# Athena V12.5 — Fluxo de Relevância Humana

## Princípio

A Athena usa LLMs para interpretar linguagem, relevância e follow-ups. A Athena Core continua decidindo persistência, atualização do World Model, raciocínio e resposta final.

## Fluxo

```text
Mensagem
↓
IntentResolutionEngine
↓
TargetResolutionEngine
↓
RelevanceEngine inicial
↓
ConversationRouter
↓
Athena Core
↓
KnowledgeExtractionEngine, se houver aprendizado
↓
RelevanceEngine com conhecimento extraído
↓
ConsolidationPlanner
↓
MemoryManager / WorldModel / ReasoningEngine
↓
FollowUpQuestionEngine
↓
NaturalResponseEngine
```

## Módulos

- `relevance/relevance_engine.py`: avalia `relevance_score`, `emotional_score`, `relationship_score`, `identity_score`, `future_score` e `memory_priority`.
- `relevance/consolidation_planner.py`: decide armazenamento curto, médio, candidato longo, confirmação e atualização do World Model.
- `relevance/follow_up_question_engine.py`: gera pergunta contextual quando a relevância indicar que faz sentido.
- `relevance/relationship_relevance_engine.py`: extrai sinais estruturais de entidades e relações já extraídas.
- `relevance/emotional_relevance_engine.py`: normaliza os scores numéricos.

## Memória

A tabela `memory_relevance` registra metadados sem substituir as tabelas existentes:

- scores de relevância;
- prioridade de memória;
- entidades relacionadas;
- necessidade de confirmação;
- pergunta de follow-up;
- razão semântica retornada pela LLM.

## Respostas

Consultas de entidade usam resposta natural por padrão. O modo técnico é preservado quando a intenção estruturada traz `mode=technical` ou operação técnica equivalente.

## Tool Honesty

Pedidos de informação externa continuam exigindo ferramenta. Se não houver executor/fonte configurada, a Athena responde a limitação explicitamente e não inventa dados.
