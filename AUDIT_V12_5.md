# AUDIT V12.5 — Relationship Memory, Emotional Relevance & Human Meaning

## 1. Resumo da V12.5

A V12.5 adiciona uma camada controlada de relevância humana sem reescrever a V12.4.

Fluxo preservado:

```text
Mensagem -> Intent/Target via LLM -> Athena Core -> Memory/WorldModel/Reasoning/ToolAwareness -> NaturalResponseEngine
```

Novo fluxo para aprendizado:

```text
learning -> KnowledgeExtractionEngine -> RelevanceEngine -> ConsolidationPlanner -> MemoryManager/WorldModel -> FollowUpQuestionEngine -> resposta natural
```

O princípio permanece:

```text
Athena usa LLMs. LLMs não são Athena.
```

## 2. Histórico de relevância, emoção, curiosidade e importância

Arquivos encontrados:

- `AUDIT_V11.md`
- `AUDIT_V12.md`
- `AUDIT_V12_1.md`
- `AUDIT_V12_2.md`
- `AUDIT_V12_3.md`
- `AUDIT_V12_4.md`
- `memory_interpreter.py`
- `memory_manager/memory_manager.py`
- `curiosity/curiosity_engine.py`
- `reasoning/reasoning_engine.py`
- `conversation/natural_response_engine.py`
- `conversation/intent_resolution_engine.py`
- `conversation/target_resolution_engine.py`
- `world_model/knowledge_extraction_engine.py`
- `brain/orchestrator.py`
- `inspect_memory.py`

Versões anteriores:

- V8.2 aparece em docstrings de `MemoryInterpreter` e `KnowledgeExtractionEngine` como LLM-first para relevância/extração. Não foi encontrado `AUDIT_V8*.md`.
- V11 removeu parsers legados e introduziu raciocínio/agência estruturados. Também deixou `CuriosityEngine` baseado em recorrência, importância e densidade relacional.
- V12 adicionou GUI, Self Code Awareness e Git Read Awareness.
- V12.1 endureceu SQLite, GUI e error awareness.
- V12.2 colocou conversa antes de aprendizado.
- V12.3 adicionou `NaturalResponseEngine`, métricas e maturidade conversacional.
- V12.4 tornou intenção/alvo LLM-first e criou `TargetResolutionEngine`.

## 3. O que já existia

- `IntentResolutionEngine` LLM-first.
- `TargetResolutionEngine`.
- `ConversationRouter` sem fast-path por palavras no caminho principal.
- `MemoryInterpreter` LLM-first, mas com poucos campos.
- `MemoryManager` com curto, médio e candidatos longos por recorrência/score.
- `WorldModel` com entidades, relações, eventos e estados.
- `ReasoningEngine` com raciocínio via LLM sobre evidências estruturadas.
- `NaturalResponseEngine` para respostas curtas e naturais.
- `ToolRegistry` para tool awareness.

## 4. O que falhou

- Relevância humana não era usada na decisão de memória.
- `MemoryManager` ainda dependia demais de recorrência e score simples.
- Informação emocional central podia cair em `greeting` ou resposta genérica.
- Consulta de entidade respondia tecnicamente por padrão.
- Aprendizado primeiro salvava texto cru e só depois tentava World Model.
- Relações múltiplas podiam ser compactadas em uma única relação.
- `inspect_memory.py` não exibia relevância emocional, candidatos longos nem follow-ups.

## 5. O que foi reaproveitado

- V12.4: Intent/Target LLM-first.
- V12.2: Orchestrator conversation-first.
- V8.2: extração estrutural via LLM.
- V11: ReasoningEngine baseado em evidências.
- V12.3: NaturalResponseEngine e métricas.
- Tabelas existentes de memória e World Model.

## 6. O que foi substituído

Não houve substituição total de subsistemas.

Foi evoluído:

- `MemoryInterpreter` passou a retornar scores emocionais/relacionais/identitários/futuros.
- `MemoryManager.observe()` passou a aceitar relevância e plano de consolidação.
- O caminho `learning` do Orchestrator agora usa relevância e consolidação antes da resposta final.
- Consulta de entidade passou a usar resposta natural por padrão.

## 7. O que não deve ser recriado do zero

- `MemoryManager`
- `WorldModel`
- `IntentResolutionEngine`
- `TargetResolutionEngine`
- `NaturalResponseEngine`
- `ReasoningEngine`
- `ToolRegistry`

## 8. Arquivos analisados

- `AUDIT_V*.md`
- `brain/orchestrator.py`
- `memory/database.py`
- `memory_interpreter.py`
- `memory_manager/memory_manager.py`
- `curiosity/curiosity_engine.py`
- `reasoning/reasoning_engine.py`
- `conversation/*`
- `world_model/*`
- `self_model/self_model.py`
- `inspect_memory.py`
- `gui/chat_panel.py`
- `core/context_builder.py`

## 9. Arquivos alterados nesta etapa V12.5

- `brain/orchestrator.py`
- `conversation/conversation_router.py`
- `conversation/intent_resolution_engine.py`
- `core/context_builder.py`
- `gui/chat_panel.py`
- `inspect_memory.py`
- `memory/database.py`
- `memory_interpreter.py`
- `memory_manager/memory_manager.py`
- `reasoning/reasoning_engine.py`
- `world_model/knowledge_extraction_engine.py`

Arquivos criados:

- `relevance/__init__.py`
- `relevance/relevance_engine.py`
- `relevance/emotional_relevance_engine.py`
- `relevance/relationship_relevance_engine.py`
- `relevance/follow_up_question_engine.py`
- `relevance/consolidation_planner.py`
- `docs/V12_5_RELEVANCE_FLOW.md`
- `tests/__init__.py`
- `tests/test_v12_5.py`
- `AUDIT_V12_5.md`

Observação: o worktree já tinha alterações anteriores em `README.md`, `config/settings.json`, `conversation/identity_engine.py`, `conversation/intent_interpreter.py`, `conversation/response_planner.py`, `core/settings.py`, `gui/settings_panel.py`, `main.py`, banco/logs e `__pycache__`.

## 10. Como RelevanceEngine funciona

`RelevanceEngine` recebe:

- mensagem;
- intenção/alvo resolvidos;
- contexto recente;
- conhecimento extraído, quando disponível;
- entidades conhecidas;
- identidade do usuário e da Athena.

Ele retorna:

```json
{
  "relevance_score": 0,
  "emotional_score": 0,
  "relationship_score": 0,
  "identity_score": 0,
  "future_score": 0,
  "memory_priority": "ignore|short|mid|long_candidate|long_confirm",
  "should_ask_follow_up": false,
  "follow_up_question": "",
  "reason": "",
  "risks": []
}
```

O fallback sem LLM é estrutural e conservador. Ele não interpreta emoção por frase.

## 11. Como Emotional Relevance funciona

`EmotionalRelevanceEngine` normaliza scores de 0 a 100 e expõe decisão mínima de preservação por pontuação. A interpretação semântica fica na LLM; o Core só valida números e prioridades.

## 12. Como Relationship Memory funciona

A tabela `memory_relevance` registra metadados de memória:

- `relevance_score`
- `emotional_score`
- `relationship_score`
- `identity_score`
- `future_score`
- `memory_priority`
- `related_entities_json`
- `confirmation_required`
- `confirmed`
- `follow_up_question`
- `reason`

Ela complementa as camadas existentes, sem criar um banco paralelo.

## 13. Como Follow-up Question Engine funciona

`FollowUpQuestionEngine` só pergunta quando `RelevanceEngine` ou o plano de consolidação indicam que faz sentido. A pergunta vem da LLM a partir da relevância, alvo e conhecimento extraído. O fallback usa alvo/entidade estruturada quando existe.

## 14. Como Consolidation Planner funciona

`ConsolidationPlanner` transforma score e prioridade em plano:

- salvar curto prazo;
- salvar médio prazo;
- registrar candidato longo;
- exigir confirmação;
- atualizar World Model;
- perguntar follow-up.

Ele usa thresholds numéricos e estruturas extraídas, não frases do usuário.

## 15. Como evita hardcode

Auditoria executada:

```bash
rg -n "Fernanda|Francisco|amor da minha vida|amiga|gosto muito|clima|notícias|noticias|Rewell" brain conversation core memory memory_manager relevance reasoning world_model gui inspect_memory.py memory_interpreter.py -S
```

Resultado em código de produção:

- Não há `Fernanda`, `Francisco`, `amor da minha vida`, `amiga`, `gosto muito`, `clima`, `notícias` como regra cognitiva.
- `Rewell` aparece como default de identidade/configuração já existente ou fallback de identidade.
- As frases e nomes dos casos reais aparecem nos testes, onde são permitidos.

Auditoria de regex:

```bash
rg -n "import re|from re import|re\\.search|re\\.match|re\\.sub|regex" brain conversation core memory memory_manager relevance reasoning world_model gui inspect_memory.py memory_interpreter.py -S
```

Resultado:

- Nenhum regex cognitivo novo.
- Ocorrências são configurações/documentação legada de fallback regex ou texto explicativo.

## 16. Como evita chatbot

Não existe fluxo `mensagem -> LLM -> resposta final` para aprendizado.

O fluxo usado é:

```text
Intent/Target -> Core -> extração -> relevância -> plano -> memória/world/reasoning/tool -> resposta natural
```

A LLM não grava diretamente, não atualiza o banco sozinha e não executa ferramenta.

## 17. Como evita fingir sentimentos humanos

Prompts de relevância, follow-up e resposta natural instruem explicitamente:

- reconhecer importância;
- não dizer que Athena sente como humano;
- em relações com Athena, declarar limitação de sentimento humano quando necessário.

## 18. Tool Honesty

`external_information` continua exigindo `requires_tool=true`.

Se não houver ferramenta/fonte configurada, a Athena responde:

- que não possui fonte/executor em tempo real;
- que não vai inventar dado externo.

Isso cobre clima e notícias sem hardcode por palavra no Core.

## 19. Testes executados

Comando literal pedido:

```bash
python -m py_compile $(find . -name '*.py')
```

Resultado:

```text
/bin/bash: python: command not found
```

Equivalente disponível:

```bash
python3 -m py_compile $(find . -name '*.py')
```

Resultado:

```text
sem erros
```

Comando literal pedido:

```bash
python inspect_memory.py
```

Resultado:

```text
/bin/bash: python: command not found
```

Equivalente disponível:

```bash
python3 inspect_memory.py
```

Resultado:

```text
exibiu seções V12.5 e terminou com aviso controlado:
DatabaseError: database disk image is malformed
```

Teste automatizado:

```bash
python3 -m unittest tests.test_v12_5
```

Resultado:

```text
Ran 1 test in 0.232s
OK
```

## 20. Saída dos testes V12.5

A suíte cobre:

- pai/Francisco;
- pronome resolvido para Francisco;
- consulta natural sobre Francisco;
- Fernanda como relação central com múltiplas relações;
- consulta natural sobre Fernanda;
- modo técnico explícito;
- Athena como amiga;
- criador acredita no futuro;
- afeto por Athena sem fingir sentimentos;
- raciocínio de sogro;
- explicação da conclusão;
- clima sem fonte;
- notícias sem fonte;
- regressão de identidade;
- conversa longa emocional não classificada como saudação.

## 21. Limitações restantes

- A qualidade da relevância depende da LLM local.
- A qualidade dos rótulos relacionais depende da extração LLM.
- Confirmações pendentes de memória longa ainda não possuem fluxo completo de aprovação separado.
- O banco local `knowledge.db` atual acusa `database disk image is malformed` ao inspecionar tabelas de agência. A V12.5 não tentou reparar ou substituir o banco do usuário.
- Ainda não há executor real de clima/notícias/internet.
- O fallback natural sem LLM é seguro, mas menos expressivo.

## 22. O que fica para V13

- Migrações formais versionadas para SQLite.
- Fluxo dedicado para confirmar/rejeitar `long_confirm`.
- Separar executor real de ferramentas do catálogo de capacidades.
- Melhorar raciocínio relacional com explicações mais naturais.
- Criar painel debug dedicado em vez de apenas status textual.
- Reduzir `__pycache__`/artefatos gerados no repositório.
- Detecção estatística/embedding para recorrência sem stopwords manuais.

## 23. Checklist final de aceite

- [x] “Fernanda é o amor da minha vida” não recebe importância 0 nos testes V12.5.
- [x] “Você é minha amiga” não é ignorado nos testes V12.5.
- [x] “Quem é Fernanda?” responde com memória aprendida nos testes.
- [x] “Se eu casar com Fernanda, o que meu pai será dela?” infere sogro nos testes.
- [x] “Qual a previsão do clima?” não inventa e não responde saudação nos testes.
- [x] Athena faz follow-up contextual em informação emocional relevante nos testes.
- [x] `inspect_memory.py` exibe memórias emocionais/scores/candidatos/follow-ups.
- [x] GUI e terminal continuam usando `Athena.chat()`.
- [x] Nenhum regex cognitivo novo foi criado.
- [x] Nenhum hardcode de frases emocionais foi adicionado à lógica cognitiva.
- [x] Nenhum hardcode de Fernanda/Francisco/Rewell foi adicionado à lógica cognitiva; `Rewell` permanece apenas identidade/default.
- [x] Testes automatizados passam com `python3`.
- [x] `py_compile` passa com `python3`.
- [x] `AUDIT_V12_5.md` foi gerado.
