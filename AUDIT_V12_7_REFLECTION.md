# AUDIT V12.7-pre - Reflection Foundation

## Resumo executivo

Esta fase implementa a primeira base de autoavaliação segura da Athena.

A Athena agora pode observar uma resposta já produzida, detectar classes genéricas de falha, registrar uma hipótese estruturada, sugerir melhoria, sugerir teste e manter a exigência de revisão humana.

Isto segue a arquitetura:

- Athena = sistema cognitivo.
- GUI = boca/rosto.
- Core = coordenação.
- Reflection = autoavaliação.
- Memory/World Model = experiência acumulada.
- Qwen = linguagem/raciocínio auxiliar futuro.
- spaCy = percepção linguística local futura.

## Diagnóstico

A V12.6 melhorou rotas locais, consulta de entidade, resolução de pronome/fuzzy e redução de LLM em rotas simples.

O próximo risco arquitetural era fazer a Athena apenas responder melhor, mas sem perceber quando erra.

A correção desta fase é criar um órgão de reflexão que não decide sozinho e não altera código sozinho.

## Implementado

Arquivos criados:

- `reflection/reflection_store.py`
- `tests/test_reflection_engine.py`
- `tests/manual_reflection_v12_7.py`
- `docs/REFLECTION_ENGINE.md`
- `AUDIT_V12_7_REFLECTION.md`

Arquivos alterados:

- `reflection/reflection_engine.py`
- `brain/orchestrator.py`
- `core/settings.py`
- `tests/test_v12_5.py`

## ReflectionEngine

O `ReflectionEngine` agora possui:

- `observe_turn(...)`
- `analyze_turn(...)`
- `recent_events(...)`
- relatório local de melhoria;
- detectores locais sem LLM obrigatória.

Detectores:

- `unknown_loop`
- `wrong_target`
- `missing_pronoun_resolution`
- `recent_entity_resolution_failed`
- `llm_overuse`
- `tool_hallucination`
- `pending_confirmation_blocking_topic_switch`
- `slow_known_recall`

## ReflectionStore

O `ReflectionStore` salva eventos em JSONL local:

`logs/reflection_events.jsonl`

Esse caminho é runtime/local artifact e já fica fora do Git por causa de `logs/*`.

## LLM Critic / Qwen

Não foi implementado nesta fase.

Decisão: adiado de propósito.

Motivo: primeiro a Athena precisa de reflexão local confiável. Qwen pode entrar depois como crítico auxiliar, com timeout, limite de chamadas e `accepted=false` por padrão.

## spaCy / LinguisticEngine

Não foi implementado nesta fase.

Decisão: adiado de propósito.

Motivo: a V12.6 já cobre várias rotas locais com `CognitiveControlEngine` e `ConversationContext`. spaCy deve entrar como percepção linguística opcional apenas quando houver falhas reais que justifiquem a dependência.

## Memory Pipeline / Workers

Não foi implementado nesta fase.

Decisão: preparar, não fingir.

O metadata agora inclui campos para reflexão/fila, mas `AsyncReflectionLoop`, `MemoryWorker`, `ConsolidationWorker` e `WorldModelWorker` ficam como próximos passos.

## Exemplo de ReflectionEvent

```json
{
  "issue_type": "wrong_target",
  "severity": "high",
  "suspected_module": "CognitiveControlEngine/TargetResolution",
  "explanation": "A resposta mencionou limitacoes emocionais da Athena em uma rota sobre alvo externo.",
  "suggestion": "Aplicar a guarda de self-feeling somente quando o alvo for Athena ou uma pergunta de identidade da propria Athena.",
  "requires_human_review": true,
  "accepted": false
}
```

## Regras preservadas

- Reflection não edita código.
- Reflection não faz commit.
- Reflection não faz push.
- Reflection não transforma Qwen em cérebro.
- Reflection não torna spaCy obrigatório.
- Reflection não substitui Memory/World Model.
- Reflection gera hipótese, não verdade absoluta.
- Humano aprova mudanças perigosas.

## Próximos passos recomendados

1. Criar `AsyncReflectionLoop` com fila em memória e `process_pending_once()`.
2. Criar `SelfImprovementMemory` ou mapear ReflectionEvents para memória procedural.
3. Avaliar `LlmCriticEngine` com Qwen opcional.
4. Avaliar `LinguisticEngine` com spaCy opcional.
5. Criar `MemoryPipeline` com WorkingMemory, ShortTermMemory e consolidação assíncrona.
6. Adicionar HumanApprovalGate para aceitar/rejeitar sugestões de melhoria.
