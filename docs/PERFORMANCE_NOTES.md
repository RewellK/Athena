# V12.6 Performance Notes

## Principio

Athena deve usar LLMs como ferramenta, nao como fonte permanente de inteligencia. Consultas locais conhecidas devem priorizar estruturas internas.

## Fast paths locais

Classes locais aceitas:

- startup greeting
- greeting / small talk curto
- self identity
- user identity
- capability query
- entity query
- pending confirmation
- error/status
- external tool missing

Esses caminhos classificam categorias operacionais, nao fatos cognitivos especificos.

## Metricas adicionadas

Cada resposta pode registrar:

- `llm_calls`
- `intent_llm_calls`
- `relevance_llm_calls`
- `extraction_llm_calls`
- `reasoning_llm_calls`
- `natural_response_llm_calls`
- `follow_up_llm_calls`
- `duration_ms`
- `total_duration_ms`
- `tts_duration_ms`

As metricas sao gravadas em `logs/conversation_metrics.jsonl` quando `conversationMetricsEnabled` esta ativo.

## Alvos V12.6

- startup greeting: 0 LLM calls
- greeting simples: 0 LLM calls
- self identity: 0 LLM calls
- capability query: 0 LLM calls
- pending confirmation: 0 LLM calls
- known entity query: 0 LLM calls quando resposta local e suficiente
- learning novo: LLM permitido
- reasoning complexo: LLM permitido

## Como inspecionar

Use:

```bash
python3 inspect_memory.py
```

O script mostra as ultimas metricas de conversa quando o arquivo de log existe.
