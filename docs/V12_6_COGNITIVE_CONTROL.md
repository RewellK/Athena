# V12.6 Cognitive Control

## Principio

Athena usa LLMs, mas LLMs nao sao Athena. A V12.6 adiciona uma camada explicita de controle cognitivo local para decidir quando o Core pode agir com estruturas proprias antes de chamar uma LLM.

## Camada Criada

`conversation/cognitive_control_engine.py` contem o `CognitiveControlEngine`.

Ele nao extrai fatos completos, nao responde perguntas factuais sozinho e nao contem nomes especificos. A responsabilidade dele e decidir rotas locais de baixo risco:

- `greeting`
- `small_talk`
- `self_identity`
- `user_identity`
- `entity_query`
- `capability_query`
- `teach_intent`
- `pending_confirmation`
- `external_information`
- `error_query`
- `unknown_recovery`
- `learning_candidate`

## Fluxo

1. A GUI chama `Athena.chat()`.
2. `ConversationRouter` consulta o `CognitiveControlEngine`.
3. Se a rota local for clara, o Core usa Memory, World Model, SelfModel, CapabilityEngine, ErrorAwareness ou ToolRegistry sem LLM de intencao.
4. Se a rota local nao for clara, o `IntentResolutionEngine` pode usar LLM.
5. Se a LLM estiver indisponivel ou retornar baixa confianca, o roteador tenta novamente o fallback local.
6. O Core decide se aprende, consulta, raciocina, pede confirmacao ou responde.

## Local vs LLM

Rotas locais claras evitam pipeline pesado:

- saudacao simples
- identidade da Athena
- identidade do usuario/criador
- perguntas diretas sobre entidade
- perguntas sobre capacidades
- recuperacao de erro de classificacao
- pedidos de informacao externa atual sem ferramenta
- confirmacao pendente com `sim` ou `nao`

LLM continua sendo usada quando:

- a mensagem exige interpretacao semantica detalhada
- ha aprendizado novo que precisa virar estrutura
- a relevancia humana precisa ser estimada
- a resposta natural nao pode ser montada com fatos locais
- ha raciocinio complexo

## Consultas de Entidade

Perguntas explicitas como `quem e X?`, `voce sabe quem e X?`, `consegue me falar quem e X?` e `o que voce sabe sobre X?` viram `entity_query`.

Se a entidade ja existe no World Model, Athena responde localmente. Se nao existe, responde que ainda nao tem informacao suficiente, sem cair em `unknown` e sem transformar a pergunta em aprendizado.

## Aprendizado

Afirmações ensinaveis claras viram `learning_candidate`. O controle cognitivo apenas identifica que aquilo parece aprendizado; a extracao detalhada continua no World Model e pode usar LLM quando configurada.

Com `useLLM=false`, Athena reconhece a tentativa de ensino, mas nao finge que estruturou conhecimento.

## Multiplos Assuntos

Mensagens como `Hoje meu dia foi muito bom, o que voce pode fazer?` preservam a pergunta principal como `capability_query` e carregam metadata `positive_day_context`, permitindo resposta combinada:

1. reconhecer o contexto emocional leve;
2. responder capacidades via `CapabilityEngine`.

## Confirmacao Pendente

Confirmacoes pendentes nao bloqueiam troca de assunto. Se houver pendencia e o usuario perguntar `quem e voce?`, Athena responde identidade e mantem a pendencia. Se o usuario disser `sim` ou `nao`, a confirmacao e resolvida localmente.

## Unknown Recovery

`o que voce nao entendeu?` usa `unknown_recovery`. Se houver falha recente, Athena explica a rota, fonte e confianca. Se nao houver falha recente, diz isso explicitamente em vez de repetir o fallback.

## Metricas

As respostas agora expoem:

- `llm_calls`
- `llm_call_count`
- `intent_llm_calls`
- `relevance_llm_calls`
- `extraction_llm_calls`
- `reasoning_llm_calls`
- `natural_response_llm_calls`
- `follow_up_llm_calls`
- `duration_ms`
- `total_duration_ms`
- `tts_ms`
- `used_memory`
- `used_world_model`
- `used_llm`
- `pending_confirmation`

## Anti-Hardcode

O controle cognitivo nao contem nomes como Fernanda, Francisco ou Rewell, e nao responde conhecimento por nomes fixos. Exemplos com esses nomes existem apenas em testes e transcript.

Termos de capacidade e intencao sao classes operacionais genericas, nao conhecimento cognitivo sobre pessoas.

## Estado Para V13

Athena esta preparada para iniciar V13, mas a V13 deve continuar usando o Core como cerebro. Desktop Presence deve ser interface e presenca, nao substituto de Memory, World Model, Reasoning, SelfModel, Context, Agency ou Relevance.
