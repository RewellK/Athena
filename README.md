# Athena V11 — Agency & Action Foundation Lockdown

Athena é uma entidade digital persistente em evolução.

Princípio central:

> Athena usa LLMs. LLMs não são Athena.

A V11 transforma Athena de um sistema que responde com conhecimento para uma arquitetura capaz de iniciar o ciclo:

```text
Conhecimento
↓
Intenção
↓
Objetivo
↓
Plano
↓
Ação proposta
↓
Aprovação humana
↓
Resultado
↓
Reflexão
```

## O que mudou na V11

A V11 não adiciona regras comportamentais. Ela adiciona uma fundação para agência controlada.

Novo pacote:

```text
agency/
├── intention_engine.py
├── agency_engine.py
├── goal_engine.py
├── action_engine.py
├── tool_registry.py
├── proactivity_engine.py
└── json_utils.py
```

## Regra arquitetural

O Orchestrator não interpreta significado.

Ele apenas:

```text
recebe
coordena
delega
retorna
```

Toda interpretação deve seguir:

```text
Texto
↓
LLM
↓
JSON estrutural
↓
Athena Core
↓
Validação
↓
Persistência / Planejamento
```

## Novas tabelas SQLite

A V11 adiciona:

```text
intentions
agency_goals
plans
tool_registry
actions
outcomes
```

Essas tabelas permitem que Athena lembre:

- o que interpretou como intenção
- quais objetivos cognitivos propôs
- quais planos criou
- quais ferramentas estavam disponíveis
- quais ações foram propostas
- quais resultados ocorreram

## Execução

Na raiz do projeto:

```bash
python main.py
```

ou:

```bash
python athena.py
```

O bootstrap continua automático.

## Configuração

Arquivo:

```text
config/settings.json
```

Campos importantes da V11:

```json
{
  "agencyEnabled": true,
  "humanApprovalRequired": true,
  "autoExecuteActions": false,
  "autoLearnPermanentKnowledge": false,
  "allowCognitiveRegex": false,
  "allowIntentKeywordRules": false,
  "orchestratorInterpretsMeaning": false,
  "foundationLockdown": true
}
```

## Critérios de segurança cognitiva

A V11 evita:

- regex cognitivo
- parsers manuais de intenção
- gatilhos por palavra
- regras por domínio
- ações sem aprovação
- aprendizado permanente automático

## Como testar manualmente

### 1. Inicialização

```bash
python main.py
```

Resultado esperado:

```text
Athena V11 — Agency & Action Foundation Lockdown
Bootstrap automático ativo.
```

### 2. LLM indisponível

Com Ollama desligado, envie qualquer mensagem.

Resultado esperado:

```text
Não consegui interpretar isso com segurança. Pode me explicar melhor?
```

Athena não deve tentar adivinhar por regex.

### 3. Intenção estrutural

Com Ollama ligado, teste em português:

```text
Quero entender melhor como posso trabalhar fora do Brasil.
```

Resultado esperado:

- IntentionEngine interpreta intenção.
- AgencyEngine pode propor objetivo/plano.
- Athena pede autorização antes de qualquer ação.

### 4. Multilíngue

Com Ollama ligado, teste:

```text
I want to understand how to work abroad.
```

```text
Quiero entender cómo trabajar fuera de mi país.
```

Resultado esperado:

A interpretação deve vir da LLM estrutural, sem novos parsers.

### 5. Auditoria da memória

```bash
python inspect_memory.py
```

Agora o painel mostra também:

- intenções
- objetivos cognitivos
- planos
- ferramentas
- ações
- outcomes

## Auditoria V11

Leia:

```text
AUDIT_V11.md
```

Ele lista:

1. Regex restantes
2. Motivo de existência
3. Parsers restantes
4. Motivo de existência
5. Ifs restantes
6. Motivo de existência
7. Componentes ainda não totalmente generalizados
8. Próximos riscos arquiteturais

## Observação importante

A V11 prepara agência, mas não libera autonomia irrestrita.

A Athena pode propor, planejar e pedir autorização.

Ela não deve executar mudanças permanentes sem aprovação humana.
