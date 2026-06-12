# Reflection Engine V12.7-pre

## Papel cognitivo

O `ReflectionEngine` é um órgão de autoavaliação da Athena. Ele observa turnos já respondidos, detecta hipóteses de falha, sugere melhoria, sugere teste e exige revisão humana.

Ele não é a Athena inteira, não substitui o Core e não altera código sozinho.

Fluxo desejado:

1. A interface recebe a mensagem.
2. O Core coordena a resposta.
3. A resposta textual é produzida.
4. O `ReflectionEngine` observa o turno.
5. Um `ReflectionEvent` é salvo localmente quando há suspeita de falha.
6. A Athena pode relatar a hipótese ao usuário.
7. O humano aprova ou rejeita qualquer mudança perigosa.

## O que foi implementado nesta fase

Esta fase adiciona autoavaliação local e segura:

- `ReflectionEvent`: registro estruturado de uma hipótese de falha.
- `ReflectionStore`: armazenamento JSONL append-only em `logs/reflection_events.jsonl`.
- Detectores locais no `ReflectionEngine`.
- Integração pós-resposta no `Orchestrator`.
- Relatório local para perguntas como "o que você acha que precisa melhorar?".

## Detectores locais

Os detectores atuais procuram classes genéricas de falha:

- `unknown_loop`: fallback generico ou rota desconhecida repetitiva.
- `wrong_target`: resposta sobre entidade externa mencionando self-feeling da Athena.
- `missing_pronoun_resolution`: pronome recente caindo em `unknown`.
- `recent_entity_resolution_failed`: entidade recente/fuzzy ignorada antes do fallback.
- `llm_overuse`: rota simples ou recall conhecido usando LLM sem necessidade.
- `tool_hallucination`: clima/noticias/preco atual respondido sem ferramenta configurada.
- `pending_confirmation_blocking_topic_switch`: pendencia bloqueando pergunta clara.
- `slow_known_recall`: consulta conhecida lenta demais.

Esses detectores não usam hardcode cognitivo de pessoas. Nomes como Fernanda ou Francisco podem aparecer em testes, mas não na lógica do motor.

## Campos do ReflectionEvent

Cada evento registra:

- mensagem do usuário;
- resposta da Athena;
- rota, intenção e alvo;
- tipo de falha;
- severidade;
- módulo suspeito;
- explicação;
- sugestão de melhoria;
- sugestão de teste;
- `requires_human_review=true`;
- `accepted=false`.

## Qwen e spaCy

Qwen e spaCy não são obrigatórios nesta fase.

Qwen poderá entrar depois como `LlmCriticEngine` ou crítico assíncrono, mas apenas como linguagem/raciocínio auxiliar. A crítica de Qwen será hipótese, não verdade final.

spaCy poderá entrar depois como percepção linguística local, especialmente para entidades, pronomes e normalização. Athena deve continuar funcionando sem spaCy e sem modelo baixado.

## Relação com Memory/World Model

Reflection não é memória factual sobre o mundo. Ela é memória procedural/de autoaperfeiçoamento.

Conhecimento aprendido continua pertencendo a:

- `Memory`;
- `WorldModel`;
- `SelfModel`;
- `ConversationContext`;
- camadas futuras de `WorkingMemory`, `ShortTermMemory` e consolidação.

Reflection observa falhas no uso dessas estruturas e sugere melhoria.

## Segurança

Reflection não:

- edita arquivos;
- cria commits;
- faz push;
- aplica patch sozinha;
- transforma LLM em fonte de verdade;
- bloqueia a resposta principal com crítica pesada.

Toda sugestão gerada por Reflection exige revisão humana.

## Métricas

O Orchestrator adiciona ao metadata do turno:

- `reflection_ms`;
- `reflection_events`;
- `reflection_queue_size`;
- `async_jobs_pending`;
- `async_jobs_processed`.

Nesta fase a fila assíncrona real ainda não foi implementada. Os campos de fila ficam em zero para preparar a integração futura.
