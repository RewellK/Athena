# AUDIT V12.4 — LLM-Guided Intent & Target Resolution

## Objetivo

A V12.4 corrige a regressão conversacional da V12.3: a Athena não deve decidir intenção por regras locais de linguagem. A interpretação volta a ser responsabilidade da LLM, que retorna uma estrutura curta em JSON. O Athena Core apenas valida, consulta memória/World Model/ferramentas e responde.

Fluxo da V12.4:

```text
Mensagem
↓
IntentResolutionEngine / LLM
↓
JSON estrutural
↓
TargetResolutionEngine
↓
ConversationRouter
↓
Athena Core
↓
NaturalResponseEngine / módulos especializados
```

## Arquivos novos

- `conversation/intent_resolution_engine.py`
- `conversation/target_resolution_engine.py`
- `AUDIT_V12_4.md`

## Arquivos alterados

- `conversation/conversation_router.py`
- `conversation/response_planner.py`
- `conversation/intent_interpreter.py`
- `conversation/identity_engine.py`
- `brain/orchestrator.py`
- `core/settings.py`
- `config/settings.json`
- `gui/settings_panel.py`
- `README.md`

## Rotas removidas ou despriorizadas

A V12.4 remove o `IntentInterpreter` como mecanismo principal de decisão. Ele continua apenas como wrapper de compatibilidade para não quebrar imports antigos.

O caminho antigo continha fast path local com reconhecimento de perguntas e frases. Esse caminho não é mais utilizado pelo `ConversationRouter`.

## Regras removidas

Removidas do caminho principal:

- detecção local de perguntas por palavras interrogativas;
- detecção local de identidade por frases;
- detecção local de criador por frases;
- detecção local de erro por palavras;
- detecção local de sistema/Git/voz por palavras;
- detecção local de small talk por frases;
- extração local de alvo por estruturas como “quem é X”.

A interpretação dessas frases agora deve vir do JSON da LLM.

## Hardcodes removidos

Removido do caminho principal o uso de listas linguísticas para entender:

- `quem`
- `como`
- `olá`
- `bom dia`
- `erro`
- `git`
- `voz`
- `clima`
- qualquer outra frase específica

Ainda existem nomes da identidade base, como `Athena` e `Rewell`, porque fazem parte de `identity.json`, não de regras linguísticas.

## Intenções suportadas

A LLM pode retornar:

- `self_identity`
- `user_identity`
- `creator_query`
- `entity_query`
- `capability`
- `technical_capability`
- `self_status`
- `memory_query`
- `world_query`
- `reasoning`
- `learning`
- `agency`
- `system`
- `error_query`
- `external_information`
- `small_talk`
- `greeting`
- `conversation`
- `unknown`

## Targets suportados

O `TargetResolutionEngine` aceita:

- `self`
- `user`
- `entity`
- `world`
- `tool`
- `unknown`

Ele não interpreta linguagem natural. Ele só valida o alvo retornado pela LLM.

## Ferramentas reconhecidas

A V12.4 usa o `ToolRegistry` como catálogo de capacidades. A Athena não inventa resultado externo.

Se a LLM indicar `requires_tool=true` e `tool_name=weather`, por exemplo, o Athena Core procura uma ferramenta compatível no registro. Se não existir executor configurado, responde honestamente que não possui fonte/ferramenta para consultar aquilo em tempo real.

Ferramentas/capacidades atualmente registradas por padrão:

- `world_model_core`
- `knowledge_ingestion_core`
- `reasoning_core`
- `reflection_core`
- `self_code_awareness_read`
- `git_awareness_read_only`

Não há ferramenta real de clima, notícias ou internet em tempo real na V12.4.

## Onde a LLM é usada

- Resolução de intenção e alvo (`IntentResolutionEngine`).
- Extração de conhecimento, somente quando a intenção for `learning`.
- Consulta estrutural do World Model, quando necessário.
- Naturalização de algumas respostas, quando configurado.

## Onde a LLM não decide

A LLM não grava diretamente.

A LLM não altera memória.

A LLM não executa ferramenta.

A LLM não decide persistência permanente sozinha.

Ela apenas sugere estruturas.

## Limitações atuais

1. Se Ollama estiver offline, a Athena não tenta adivinhar intenção com regras locais. Ela pede esclarecimento de forma segura.
2. A meta de resolução menor que 1 segundo depende do tempo real do modelo local `qwen2.5:3b` e da máquina.
3. A V12.4 reconhece pedidos de ferramenta pela estrutura da LLM, mas ainda não possui executores externos reais para clima, notícias ou internet.
4. Algumas respostas especializadas ainda usam roteamento estrutural por intent no Orchestrator. Isso é esperado: o Core precisa delegar módulos, mas não interpreta linguagem por palavras.
5. `NaturalResponseEngine` ainda possui fallback local simples para quando a LLM não está disponível. Esse fallback não interpreta intenção nem cria conhecimento.

## Casos de borda

- JSON inválido da LLM: Athena retorna rota `unknown` e pede esclarecimento.
- LLM offline: Athena não usa regex/fallback cognitivo; informa que não conseguiu interpretar com segurança.
- Tool inexistente: Athena não inventa dados externos.
- Alvo ausente em consulta de entidade: Athena pede mais contexto.
- Confiança baixa: Athena pede esclarecimento.

## Tempo médio de resolução

No ambiente de geração, Ollama não foi usado de forma real. Testes foram feitos com provider falso para validar o fluxo estrutural. A métrica real é registrada em:

- `logs/conversation_metrics.jsonl`

Campos importantes:

- `route`
- `intent`
- `target`
- `duration_ms`
- `used_llm`
- `used_world_model`
- `used_reasoning`
- `used_agency`

## Testes executados

Com provider falso simulando o JSON da LLM:

- `Quem sou eu?` → `user_identity`, alvo `Rewell`, rota `question_about_user`.
- `Quem é você?` → `self_identity`, alvo `Athena`, rota `identity`.
- `Quem te criou?` → `creator_query`, alvo `Rewell`, rota `identity`.
- `Quem é Fernanda?` → `entity_query`, alvo `Fernanda`, rota `world_query`.
- `Como está o clima hoje?` → `external_information`, ferramenta `weather`, sem invenção de clima.
- `Oi Athena, quem é você?` → responde identidade, não saudação.
- `Fernanda é o amor da minha vida.` → rota `learning`, World Model atualizado quando extração estrutural tem confiança suficiente.

Também executado:

```bash
python -m py_compile $(find . -name '*.py')
```

Sem erros de compilação.

## Próximos riscos

1. A qualidade da conversa agora depende mais da qualidade do prompt de intenção e do comportamento do modelo local.
2. Se o modelo local retornar JSON ruim com frequência, será necessário melhorar validação, exemplos de schema e talvez usar retry estrutural curto.
3. Tool Registry ainda descreve capacidades, mas não possui executores externos reais para muitas demandas do usuário.
4. V13 deve separar melhor “catálogo de ferramentas” de “execução de ferramentas”.
5. A GUI deve expor melhor quando a intenção veio da LLM, quando houve baixa confiança e quando a Athena recusou inventar informação externa.

## Conclusão

A V12.4 restaura o princípio:

```text
LLM interpreta linguagem.
Athena Core decide.
World Model representa.
Memória armazena.
Ferramentas agem apenas quando registradas e autorizadas.
```

Se uma nova frase exigir novo `if`, a arquitetura deve ser considerada em regressão.
