# Athena V11 — Auditoria Arquitetural Foundation Lockdown

## Objetivo da auditoria

A V11 foi tratada como uma correção arquitetural, não como simples adição de funcionalidades.

Princípio aplicado:

> Athena não deve criar mais regras. Athena deve criar mais conhecimento.

O foco foi reduzir decisões cognitivas baseadas em palavras, regex, verbos, exemplos ou domínios, deslocando interpretação para:

Texto → LLM → Estrutura → Athena Core → Validação → Persistência / Planejamento

---

## 1. Regex restantes

### Resultado

Não há `import re` nem chamadas `re.search`, `re.match`, `re.sub` ou similares no código Python ativo da V11.

### Classificação

SAFE.

### Observação

Normalizações de rótulos estruturais foram reescritas usando operações simples de caracteres, sem regex cognitivo.

---

## 2. Parsers restantes

### Removidos / isolados

Foram removidos da base V11 os módulos legados que continham parsers por frase/domínio:

- `brain/goals.py`
- `brain/events.py`
- `brain/relationships.py`
- `brain/curiosity.py`

### Substituição

A interpretação agora passa por:

- `agency/intention_engine.py`
- `world_model/knowledge_extraction_engine.py`
- `world_model/query_understanding_engine.py`
- `knowledge_sources/knowledge_ingestion_engine.py`

Esses módulos pedem JSON estrutural à LLM e não possuem regras por nomes, verbos, temas ou idiomas.

### Classificação

SAFE para os módulos LLM-first.

---

## 3. Ifs restantes

A V11 ainda possui `if`, mas eles foram classificados por função arquitetural.

### SAFE — controle de fluxo não cognitivo

Exemplos:

- checar se LLM está disponível
- checar se JSON retornado é válido
- checar confiança numérica
- verificar se lista está vazia
- validar campos obrigatórios
- selecionar provider de voz configurado
- encerrar CLI com `sair`, `exit`, `quit`
- rotear por labels estruturais já produzidos pela LLM, como `route == "reasoning"`

Esses `if`s não interpretam linguagem natural diretamente.

### SAFE — roteamento estrutural

O `Orchestrator` ainda usa `if route == ...`, mas `route` é uma estrutura retornada pelo `IntentionEngine`, não uma palavra do usuário.

Classificação: SAFE.

Motivo: o Orchestrator coordena módulos. Ele não decide significado a partir de texto cru.

### SAFE — consulta de dados

Alguns engines verificam filtros estruturais, por exemplo:

- entity filter
- relationship filter
- event filter
- state filter

Classificação: SAFE.

Motivo: são filtros sobre o World Model, não parsers de linguagem.

### LEGACY/RISCO — detecção por nomes conhecidos em `ThoughtEngine`

`reasoning/thought_engine.py` ainda usa comparação textual contra entidades já conhecidas para detectar recorrência.

Classificação: LEGACY CONTROLADO.

Motivo: não há nomes hardcoded; os nomes vêm do banco. Porém ainda é uma técnica textual simples.

Risco: menções indiretas, pronomes ou traduções podem não ser detectadas.

Evolução futura recomendada: substituir por detecção estrutural via LLM + embeddings locais quando o projeto estiver pronto para isso.

---

## 4. Fallbacks restantes

### Fallback de LLM indisponível

Quando a LLM falha, a Athena não tenta adivinhar por regex.

Comportamento:

> Não consegui interpretar isso com segurança. Pode me explicar melhor?

Classificação: SAFE.

### Fallback de voz

Piper continua sendo prioridade.
macOS say continua como fallback de interface.

Classificação: SAFE.

Motivo: voz é interface, não cognição.

---

## 5. Componentes adicionados na V11

### `agency/intention_engine.py`

Transforma mensagem do usuário em intenção estruturada via LLM.

Não grava memória.
Não executa ação.
Não interpreta por palavra.

### `agency/agency_engine.py`

Coordena intenção → objetivo → plano → ação proposta.

### `agency/goal_engine.py`

Transforma intenção estruturada em objetivo cognitivo proposto.

### `agency/action_engine.py`

Transforma objetivo em plano e ações propostas.
Exige aprovação humana.

### `agency/tool_registry.py`

Registra ferramentas por capacidade, custo, latência, confiança e sucesso.

### `agency/proactivity_engine.py`

Gera iniciativa baseada em observações reais: memória intermediária, hipóteses e recorrência.

---

## 6. Persistência adicionada

Novas tabelas:

- `intentions`
- `agency_goals`
- `plans`
- `tool_registry`
- `actions`
- `outcomes`

Essas tabelas registram:

- o que Athena interpretou como intenção
- que objetivos cognitivos foram propostos
- que planos foram criados
- que ferramentas estavam disponíveis
- que ações foram propostas
- que resultados ocorreram

---

## 7. Componentes ainda não totalmente generalizados

### Thought Engine

Ainda usa ocorrência textual de entidades conhecidas.
Não depende de nomes fixos, mas ainda depende de match textual.

### Source Evaluator

Ainda usa heurísticas genéricas de fonte, como conteúdo curto, metadados e rastreabilidade.
Não é domínio-específico, mas ainda é uma heurística.

### Tool Registry inicial

Possui ferramentas internas cadastradas no bootstrap.
Isso é aceitável porque ferramentas são capacidades do sistema, não conhecimento de domínio.

---

## 8. Próximos riscos arquiteturais

1. **Transformar Action Engine em lista de automações hardcoded.**
   - Evitar criar `if ferramenta == X` para cada ação futura.

2. **Criar ferramentas por domínio cedo demais.**
   - Exemplo ruim: `SalesforceTool`, `WeatherTool`, `PortugalTool`.
   - Preferir: ferramenta genérica por capacidade.

3. **Confundir proatividade com gatilho.**
   - Proatividade deve vir de observação e hipótese, não de palavra.

4. **Permitir aprendizado permanente automático cedo demais.**
   - V11 prepara autonomia, mas ainda exige aprovação humana.

5. **Deixar a LLM virar Athena.**
   - A LLM interpreta; Athena Core valida, decide e registra.

---

## 9. Conclusão da auditoria

A V11 removeu os principais parsers legados e colocou o Orchestrator em modo lockdown.

A arquitetura agora segue:

Conhecimento
→ Intenção
→ Objetivo
→ Plano
→ Ação proposta
→ Aprovação humana
→ Resultado
→ Reflexão

A Athena ainda não possui autonomia irrestrita — e isso é intencional.

A V11 cria a fundação para agência controlada sem voltar para regras por palavra, domínio ou exemplo.
