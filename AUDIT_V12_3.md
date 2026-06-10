# AUDIT_V12_3 — Natural Conversation, Performance & GUI Polish

## 1. Rotas otimizadas

A V12.3 adicionou uma camada explícita de interpretação e planejamento conversacional:

- `conversation/intent_interpreter.py`
- `conversation/response_planner.py`
- `conversation/natural_response_engine.py`
- `conversation/conversation_memory.py`
- `conversation/conversation_metrics.py`

Rotas rápidas:

- `greeting`
- `small_talk`
- `identity`
- `creator_query`
- `question_about_user`
- `capability`
- `technical_capability`
- `self_status`
- `system`
- `error_query`

Rotas pesadas continuam delegadas:

- `learning` aciona World Model / Knowledge Extraction.
- `reasoning` aciona Reasoning Engine.
- `agency` aciona Agency Engine.
- `memory_query` aciona Reflection Engine.

## 2. Tempo médio por rota

Validação local com LLM e voz desativadas para medir o caminho rápido:

- greeting: ~0 ms
- small_talk: dezenas de ms quando há tentativa rápida de naturalização/fallback
- identity: ~0 ms
- creator_query: ~0 ms
- capability resumido: ~10 ms
- capability técnico: centenas de ms por análise de código local
- system/git/voice: poucos ms
- learning: variável, depende do Ollama e do Knowledge Extraction

As métricas reais são registradas em:

```text
logs/conversation_metrics.jsonl
```

## 3. Onde LLM é usada

A LLM é usada quando:

- a intenção não é óbvia para o caminho rápido;
- a resposta natural precisa de variação/polimento;
- a rota `learning` exige extração estrutural;
- a rota `world_query` precisa interpretar consulta estrutural;
- Reasoning, Agency ou Knowledge Sources precisam de cognição pesada.

## 4. Onde LLM não é usada

A LLM não é necessária para:

- saudação simples;
- identidade básica;
- criador;
- status básico;
- capacidade resumida;
- status de voz;
- status de Git;
- último erro;
- debug de rota.

## 5. Configurações novas

Adicionadas em `config/settings.json` e `core/settings.py`:

```json
{
  "messageReceivedSoundEnabled": true,
  "messageReceivedSoundProvider": "system_beep",
  "debugMode": false,
  "showRouteMetadata": false,
  "useNaturalResponses": true,
  "useFastConversationPath": true,
  "voiceRate": 180,
  "voiceVolume": 1.0,
  "voiceProfile": "default",
  "llmTimeoutSeconds": 30,
  "conversationMetricsEnabled": true,
  "naturalResponseForSmallTalk": true
}
```

## 6. Testes executados

Executado:

```bash
python -m py_compile $(find . -name '*.py')
```

Teste conversacional local na mesma instância de `Athena.chat()`:

- `Olá Athena`
- `Tudo bem com você?`
- `Quem é você?`
- `Quem te criou?`
- `Quem é Rewell?`
- `Oi Athena, quem é você?`
- `O que você consegue fazer?`
- `Me mostre tecnicamente seus módulos`
- `Você está usando Git?`
- `Você consegue falar?`
- `Meu pai se chama Francisco.`

Resultado:

- sem crash;
- sem erro SQLite;
- rotas simples não chamaram World Model;
- pergunta sobre Rewell não foi confundida com identidade da Athena;
- debug/metadata disponível em `athena.last_response_metadata`.

## 7. Limitações restantes

- O caminho rápido ainda contém heurísticas genéricas de UX para saudação, identidade, status e sistema. Elas não criam conhecimento e não substituem o LLM para interpretação semântica complexa.
- Com Ollama offline, mensagens de aprendizado são roteadas de forma conservadora, mas a extração estrutural não ocorre.
- A naturalidade máxima depende do Ollama local estar disponível.
- A voz continua dependente de provider externo configurado corretamente, especialmente Piper.
- A GUI ainda é simples e não possui temas ou layout responsivo avançado.

## 8. Próximos passos para V13

Sugestões para a V13:

- separar estado conversacional por sessão;
- adicionar timeout/cancelamento visual de chamadas LLM longas;
- melhorar seleção de voz/perfil com detecção automática de providers disponíveis;
- criar testes automatizados de conversa/rotas;
- adicionar painel de métricas na GUI;
- permitir filas de mensagens em vez de apenas bloqueio de envio simultâneo;
- melhorar recuperação de entidades conhecidas sem depender de LLM quando a consulta for simples.

## 9. Nota arquitetural

A V12.3 não adiciona novas capacidades cognitivas pesadas.
Ela melhora a maturidade conversacional e a experiência de uso.

O princípio permanece:

```text
Conversar vem antes de aprender.
Aprender vem antes de agir.
Agir exige autorização.
```
