# AUDIT V12.2 — Conversational Maturity & Core Stabilization

## 1. Bugs corrigidos

### Knowledge Extraction como entrada principal

Problema: mensagens simples podiam chegar ao World Model/Knowledge Extraction antes de serem entendidas como conversa, identidade, status, capacidade ou erro.

Correção: `brain/orchestrator.py` agora chama `ConversationRouter` antes de qualquer aprendizado estrutural.

### Erro `_build_generic_event_name` ausente

Problema: `world_model/knowledge_extraction_engine.py` chamava `self._build_generic_event_name(...)`, mas o método não existia.

Correção: método implementado de forma genérica, sem depender de domínio, nomes, verbos ou exemplos específicos.

### Normalização frágil de JSON da LLM

Problema: listas ausentes, `None`, objetos isolados ou JSON parcial podiam quebrar normalização.

Correção: adicionado `_as_list()` e normalização defensiva em entidades, relações, eventos, estados, participantes e referências temporais.

### Perguntas de status confundidas com aprendizado

Problema: perguntas como “Como você está?” ou “Qual foi seu último erro?” podiam cair em fluxo semântico inadequado.

Correção: rotas dedicadas `self_status` e `error_query`.

### Consulta de voz confundida com Git/status genérico

Problema: `operation=status` podia ser tratado como Git antes de voz.

Correção: `brain/orchestrator.py` prioriza `subsystem=voice` antes da rota Git.

## 2. Rotas conversacionais criadas

Arquivos novos:

```text
conversation/
  __init__.py
  conversation_context.py
  conversation_router.py
  conversation_engine.py
  identity_engine.py
  capability_engine.py
  self_status_engine.py
```

Rotas suportadas:

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
- `conversation`
- `unknown`

## 3. Health Engine criado

Arquivos novos:

```text
health/
  __init__.py
  health_engine.py
  health_snapshot.py
```

O Health Engine verifica, de forma defensiva:

- LLM
- SQLite
- Voice
- Git
- Memory
- World Model
- Agency
- último erro registrado

## 4. Problemas restantes

### Classificação conversacional ainda depende da LLM para generalização completa

Quando Ollama está ativo, a rota vem da LLM em JSON estrutural.
Quando Ollama está offline, existe fallback local conservador apenas para rotas operacionais/small talk básicas.

Esse fallback não grava conhecimento e não chama Knowledge Extraction, mas ainda contém marcadores textuais de UX. Ele foi mantido para estabilidade desktop e deve ser reduzido futuramente com um classificador local melhor.

### Aprendizado estrutural offline ainda é limitado

Sem Ollama, Athena não tenta aprender por regex. Isso preserva a arquitetura LLM-first, mas limita aprendizado offline.

### GUI não foi aberta neste ambiente

`customtkinter` pode estar ausente no ambiente de validação. O fallback de dependência ausente continua preservado.

## 5. Casos de borda cobertos

- Evento sem nome: gera nome genérico estrutural.
- Evento sem tipo: usa `generic_event`.
- Relação sem target: ignorada sem crash.
- Entidade sem nome: ignorada sem crash.
- State vazio: ignorado sem crash.
- Confidence ausente: normalizada com default seguro.
- Date ausente: aceita string vazia.
- JSON parcial: campos ausentes viram listas vazias.
- JSON inválido: extração vazia e Athena pede contexto.
- Lista vazia: não salva conhecimento.
- Último erro ausente: resposta amigável.

## 6. Limitações conhecidas

- O Conversation Router ideal ainda depende da disponibilidade do Ollama para interpretação semântica multilíngue plena.
- O fallback local é propositalmente pequeno e não deve crescer como inteligência cognitiva.
- A rota `learning` não deve ser emulada por regex quando a LLM estiver offline.
- A conversa natural sem LLM é limitada a respostas curtas e operacionais.

## 7. Cobertura dos testes executados

Comandos executados:

```bash
python -m py_compile $(find . -name '*.py')
python inspect_memory.py
```

Teste conversacional de 20 mensagens executado com uma mesma instância de `Athena.chat()`.

Mensagens testadas:

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

Resultado observado:

- sem crash
- sem erro SQLite
- sem stacktrace cru
- sem Knowledge Extraction em small talk/status/identidade
- respostas operacionais estáveis

## 8. Preparação para V13

Recomendações:

1. Criar um classificador local leve treinável ou baseado em exemplos aprendidos pela própria Athena, sem regex crescente.
2. Criar testes automatizados formais para rotas conversacionais.
3. Separar memória efêmera de sessão da memória persistente de forma ainda mais explícita.
4. Adicionar telemetria local de estabilidade da GUI.
5. Criar um modo de diagnóstico desktop para reproduzir falhas com segurança.

## 9. Conclusão

A V12.2 corrige o problema central identificado nos testes reais:

> Athena não deve tentar aprender antes de conversar.

Agora a entrada passa por uma camada conversacional antes de qualquer tentativa de extração, aprendizado, raciocínio ou agência.
