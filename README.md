# Athena V12.2 — Conversational Maturity & Core Stabilization

Athena V12.2 mantém o princípio central:

> Athena usa LLMs. LLMs não são Athena.

Esta versão não adiciona uma nova capacidade cognitiva pesada. Ela corrige o fluxo central para que Athena converse antes de tentar aprender.

## Mudança arquitetural principal

Fluxo antigo problemático:

```text
Mensagem → Knowledge Extraction → possível erro / resposta ruim
```

Fluxo V12.2:

```text
Mensagem
↓
Conversation Router
↓
Rota conversacional
↓
Módulo correto
↓
Resposta
```

Knowledge Extraction só é chamado quando a rota é `learning`.

## Rotas conversacionais

```text
conversation/
  conversation_router.py
  conversation_context.py
  conversation_engine.py
  identity_engine.py
  capability_engine.py
  self_status_engine.py
```

Rotas mínimas suportadas:

- `greeting`
- `small_talk`
- `identity`
- `capability`
- `self_status`
- `memory_query`
- `world_query`
- `reasoning`
- `learning`
- `agency`
- `system`
- `error_query`

## Health Engine

```text
health/
  health_engine.py
  health_snapshot.py
```

Permite responder perguntas como:

- Como você está?
- Você está funcionando corretamente?
- Você está usando Git?
- Você consegue falar?

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

## Testes conversacionais sugeridos

```text
Olá Athena
Tudo bem?
Quem é você?
Como você está?
O que você consegue fazer?
Qual foi seu último erro?
Você está usando Git?
Você consegue falar?
```

Resultado esperado:

- nenhum crash
- nenhuma tentativa de Knowledge Extraction
- nenhuma mensagem “não consegui transformar isso em conhecimento estruturado”
- respostas naturais ou operacionais

## Testes de aprendizado sugeridos

Com Ollama ativo:

```text
Meu pai se chama Francisco.
Francisco comprou um Gol em 2023.
Minha mãe se chama Débora.
```

Resultado esperado:

- Conversation Router classifica como `learning`
- Knowledge Extraction é acionado
- JSON parcial ou ambíguo não derruba Athena
- World Model é atualizado ou Athena pede confirmação/contexto

## Resiliência

A V12.2 endurece:

- evento sem nome
- evento sem tipo
- relação incompleta
- entidade sem nome
- state vazio
- confidence ausente
- date ausente
- JSON parcial
- JSON inválido
- lista vazia
- Ollama offline
- Git indisponível
- último erro corrompido/ausente

## Auditoria

Consulte:

```text
AUDIT_V12_2.md
```

## Filosofia da V12.2

Primeiro Athena conversa.
Depois, quando necessário, ela aprende.

A conversa não é memória permanente.
Small talk não vira entidade.
Pergunta simples não vira evento.
Knowledge Extraction não é mais ponto de entrada.
