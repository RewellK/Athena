# AUDIT_V12 — Desktop + Self Code Awareness + Git Read Awareness

## 1. Arquivos novos

```text
app.py
requirements.txt
gui/__init__.py
gui/main_window.py
gui/chat_panel.py
gui/memory_panel.py
gui/world_model_panel.py
gui/agency_panel.py
gui/self_status_panel.py
gui/settings_panel.py
self_code_awareness/__init__.py
self_code_awareness/project_scanner.py
self_code_awareness/code_map_engine.py
self_code_awareness/module_analyzer.py
self_code_awareness/capability_mapper.py
self_code_awareness/limitation_detector.py
self_code_awareness/architecture_memory.py
self_code_awareness/self_code_awareness_engine.py
git_awareness/__init__.py
git_awareness/git_repository_reader.py
git_awareness/git_status_reader.py
git_awareness/git_history_reader.py
git_awareness/git_diff_reader.py
git_awareness/git_awareness_engine.py
AUDIT_V12.md
```

## 2. Arquivos alterados

```text
README.md
main.py
brain/orchestrator.py
agency/intention_engine.py
agency/tool_registry.py
core/settings.py
config/settings.json
llm/provider.py
voice/voice_engine.py
inspect_memory.py
```

## 3. Dependências novas

```text
customtkinter>=5.2.0
```

A dependência é necessária apenas para `python app.py`.
O núcleo terminal continua funcionando sem ela.

Instalação:

```bash
pip install -r requirements.txt
```

## 4. Como iniciar terminal

```bash
python main.py
```

Resultado validado neste pacote:

```text
Athena V12 — Desktop + Self Code Awareness + Git Read Awareness
Digite 'sair' para encerrar.
Bootstrap automático ativo.
Orchestrator em modo lockdown: terminal e GUI usam o mesmo Athena Core.
```

## 5. Como iniciar GUI

```bash
python app.py
```

Se `customtkinter` estiver ausente, a Athena informa:

```text
Não consegui iniciar a interface desktop da Athena.
Dependência provável ausente: customtkinter.
Instale com: pip install customtkinter
```

## 6. Limitações da GUI

- A GUI é uma superfície inicial, não um novo núcleo cognitivo.
- A GUI chama o mesmo `Athena.chat()` usado pelo terminal.
- O envio de mensagem é síncrono em uma thread simples.
- Ainda não possui histórico visual persistente separado.
- Ainda não possui temas avançados, atalhos, tray icon ou execução como serviço.
- Em ambientes sem servidor gráfico, `python app.py` não abre janela, mas informa o problema sem quebrar o núcleo.

## 7. Limitações do Git Read Awareness

- Só opera sobre a pasta local.
- Não clona automaticamente o repositório público.
- Não executa `pull` automático.
- Não cria branch.
- Não altera arquivos.
- Não faz commit.
- Não faz push.
- Não abre PR.
- Se Git não estiver instalado, informa indisponibilidade.
- Se a pasta local não for um repositório Git, informa isso e mostra a origem pública conhecida.

## 8. Provas de que Git é somente leitura

Arquivo principal:

```text
git_awareness/git_repository_reader.py
```

Comandos usados:

```text
git rev-parse --is-inside-work-tree
git rev-parse --show-toplevel
git branch --show-current
git remote -v
git status --short
git log --oneline --decorate -n <limite>
git ls-files
git diff --stat
```

Não há implementação de:

```text
git commit
git push
git pull
git checkout
git switch
git branch <nova>
git merge
git rebase
git reset
git add
git restore
git stash
```

Pedidos de mutação são respondidos com política de recusa:

```text
Na V12 eu só posso ler o Git. Ainda não posso alterar branches, criar commits, executar push, pull ou modificar arquivos.
```

## 9. Auditoria de regex, parsers e ifs cognitivos

### Regex

Resultado da auditoria AST:

```text
Importações de re: 0
from re import: 0
```

Nenhum regex cognitivo novo foi adicionado.

### Parsers cognitivos novos

Nenhum parser linguístico novo foi adicionado.

A V12 adiciona scanners estruturais:

```text
ProjectScanner
CodeMapEngine
ModuleAnalyzer
CapabilityMapper
GitRepositoryReader
```

Esses componentes analisam arquivos, AST e Git. Eles não interpretam intenção do usuário por palavras.

### Ifs restantes

Foram encontrados `if` operacionais na base. Classificação:

| Classe | Status | Motivo |
|---|---|---|
| `if __name__ == "__main__"` | SAFE | Ponto de entrada Python |
| `if user_input.lower() in ["sair", "exit", "quit"]` | SAFE / Terminal control | Comando de encerramento do loop, não decisão cognitiva |
| `if route == ...` no Orchestrator | SAFE / Dispatch estrutural | Roteia intenção já estruturada pela LLM; não interpreta linguagem natural |
| `if intention_type == ...` no Orchestrator | SAFE / Dispatch estrutural | Trata tipos estruturados, não palavras do usuário |
| `if operation == ...` em Git/Self Code | SAFE / Tool operation dispatch | Executa operações explícitas já normalizadas em estrutura |
| `if operation not in READ_OPERATIONS` | SAFE / Segurança | Bloqueia mutações Git na V12 |
| `if not result.available` | SAFE | Fallback técnico de disponibilidade |
| `if not include_expired`, `if status`, `if limit` | SAFE | Filtros de banco/consulta |
| stopwords em `frequent_terms` | LEGACY / Baixo risco | Lista utilitária para contagem de termos; não decide intenção nem persiste conhecimento sozinha |

Não foram adicionados ifs do tipo:

```text
if "portugal"
if "salesforce"
if "memory"
if "reasoning"
if "agency"
if "bom dia"
if "pesquise"
```

## 10. Riscos arquiteturais restantes

1. `IntentionEngine` ainda depende da LLM para escolher rotas corretamente.
2. O Orchestrator ainda possui dispatch explícito por rotas estruturadas; isso é aceitável agora, mas pode virar uma tabela de roteamento no futuro.
3. `frequent_terms` ainda possui uma lista de stopwords utilitária herdada; não é parser cognitivo, mas merece futura substituição por análise estatística/LLM-first.
4. A GUI ainda é monolítica em uma janela; no futuro pode precisar de camada ViewModel para reduzir acoplamento visual.
5. Self Code Awareness descreve estrutura e capacidades por evidência local, mas ainda não compara versões semanticamente sem Git histórico disponível.
6. Git Awareness não lê remoto diretamente; analisa apenas a cópia local.
7. `customtkinter` é dependência externa opcional e precisa ser instalada manualmente.
8. A V12 não tem sandbox de execução de código nem política refinada para futuras ações de escrita.

## 11. O que fica para V13

- Transformar dispatch do Orchestrator em registry de rotas estruturadas.
- Criar uma camada de permissões mais formal para ações futuras de escrita.
- Evoluir Self Code Awareness para detectar dívida técnica com métricas estáveis.
- Comparar versões por Git de forma mais semântica.
- Preparar Git Write Awareness com aprovação humana, mas ainda sem execução automática.
- Melhorar a GUI com histórico, abas de inspeção detalhada e refresh assíncrono.
- Remover stopwords herdadas de `frequent_terms` ou movê-las para configuração não-cognitiva.

## 12. Validação executada nesta entrega

```bash
python -m py_compile $(find . -name '*.py')
printf 'sair\n' | python main.py
python inspect_memory.py
python app.py
```

Resultado de `python app.py` neste ambiente:

```text
customtkinter ausente; fallback de mensagem funcionou.
```

Isso valida que a ausência da dependência GUI não quebra o núcleo.
