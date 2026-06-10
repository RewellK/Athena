# Athena V12.3 — Natural Conversation, Performance & GUI Polish

Athena V12.3 mantém o princípio central:

> Athena usa LLMs. LLMs não são Athena.

A V12.2 fez Athena parar de quebrar. A V12.3 faz Athena conversar melhor, responder mais rápido em rotas simples e melhorar a experiência desktop.

## Mudança arquitetural principal

Fluxo V12.3:

```text
Mensagem
↓
Intent Interpreter
↓
Response Planner
↓
Conversation Router
↓
Módulo correto
↓
Natural Response Engine
↓
Resposta + métricas
```

Knowledge Extraction continua restrita à rota `learning`.

## Novos arquivos conversacionais

```text
conversation/
  intent_interpreter.py
  response_planner.py
  natural_response_engine.py
  conversation_memory.py
  conversation_metrics.py
```

## Rotas otimizadas

Rotas simples usam caminho rápido quando seguro:

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

Rotas pesadas continuam delegadas aos módulos próprios:

- `learning`
- `world_query`
- `reasoning`
- `agency`
- `memory_query`

## Som de recebimento

Novo módulo:

```text
audio/message_sound.py
```

Configuração:

```json
{
  "messageReceivedSoundEnabled": true,
  "messageReceivedSoundProvider": "system_beep"
}
```

O som é opcional e nunca quebra o núcleo.

## GUI melhorada

A Athena Desktop agora possui:

- input limpo após envio
- botão Enviar desativado enquanto processa
- status “Athena está pensando...”
- tempo de resposta exibido
- scroll automático
- checkbox para som
- checkbox para voz
- seleção básica de provider de voz
- metadata de rota opcional em debug

## Métricas

As métricas são gravadas em:

```text
logs/conversation_metrics.jsonl
```

Cada interação registra:

- input resumido
- rota
- intenção
- duração em ms
- uso de LLM
- uso de World Model
- uso de Reasoning
- uso de Agency
- uso de voz
- uso de som

## Execução no terminal

```bash
python main.py
```

## Execução da GUI

Instale a dependência opcional:

```bash
pip install -r requirements.txt
```

Depois execute:

```bash
python app.py
```

Se `customtkinter` não estiver instalado, o núcleo continua funcionando pelo terminal.

## Testes sugeridos

```text
Olá Athena
Tudo bem com você?
Quem é você?
Quem te criou?
Quem é Rewell?
Oi Athena, quem é você?
O que você consegue fazer?
Me mostre tecnicamente seus módulos
Meu pai se chama Francisco.
Quem é Francisco?
Você está usando Git?
Você consegue falar?
```

Resultado esperado:

- saudações rápidas
- small talk natural
- identidade correta
- pergunta sobre Rewell não vira identidade da Athena
- capacidade resumida sem despejo técnico
- capacidade técnica apenas quando solicitada
- aprendizado só na rota `learning`
- GUI responsiva
- voz e som opcionais sem crash

## Auditoria

Consulte:

```text
AUDIT_V12_3.md
```

## Filosofia da V12.3

Primeiro Athena conversa.
Depois Athena aprende.
Quando necessário, Athena raciocina.
Quando autorizado, Athena age.

A naturalidade não pertence à GUI.
A naturalidade pertence ao núcleo conversacional.
