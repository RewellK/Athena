# AUDIT V12.1 — Stability & Desktop Hardening

## 1. Bugs encontrados

### Bug crítico corrigido

**Erro real observado na GUI:**

```text
SQLite objects created in a thread can only be used in that same thread.
```

Causa provável: a GUI executava `Athena.chat()` em uma thread de background, mas `MemoryDB` mantinha uma conexão SQLite criada em outra thread com `check_same_thread=True` e sem sincronização de acesso.

### Outros riscos identificados

- GUI chamava tarefas longas diretamente em alguns painéis.
- Exceções internas eram exibidas cruamente ao usuário.
- Configurações booleanas eram editáveis apenas parcialmente.
- Não existia estrutura dedicada para registrar, analisar e reportar falhas.
- Logs não eram protegidos contra escrita concorrente.

## 2. Bugs corrigidos

- Corrigido acesso SQLite entre threads.
- Corrigida exposição de exceções técnicas cruas na GUI.
- Corrigido risco de spam no botão Enviar.
- Corrigida atualização de status potencialmente bloqueante.
- Corrigidos painéis para capturar exceções e manter a aplicação viva.
- Corrigida edição de configurações booleanas por checkboxes.
- Adicionada confirmação visual para configurações sensíveis.

## 3. Problemas de thread safety

### Problema

`MemoryDB` mantinha uma conexão SQLite simples:

```python
sqlite3.connect(db_name)
```

Essa conexão não podia ser usada por uma thread diferente da thread de criação.

### Solução adotada

`MemoryDB` agora cria a conexão com:

```python
check_same_thread=False
```

Mas isso **não foi usado sozinho**.

Foi adicionada sincronização com:

```python
threading.RLock()
```

E a conexão foi encapsulada por:

- `ThreadSafeConnection`
- `ThreadSafeCursor`

Operações protegidas:

- `execute`
- `executemany`
- `cursor`
- `fetchone`
- `fetchall`
- `commit`
- `rollback`
- `close`

Também foram ativados pragmas:

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=30000;
PRAGMA foreign_keys=ON;
```

## 4. Soluções adotadas

### SQLite Hardening

Arquivo alterado:

```text
memory/database.py
```

Adicionado:

- conexão thread-safe
- lock reentrante
- WAL
- busy timeout
- método `close()`

### Background Tasks

Arquivos novos:

```text
background_tasks/__init__.py
background_tasks/task_runner.py
```

Objetivo:

- executar tarefas longas fora da thread da GUI
- manter uma fila serializada para reduzir concorrência desnecessária
- evitar congelamento da janela

### Error Awareness

Arquivos novos:

```text
error_awareness/__init__.py
error_awareness/error_capture.py
error_awareness/error_analyzer.py
error_awareness/error_reporter.py
```

Responsabilidades:

- capturar exceções
- registrar stacktrace técnico
- classificar gravidade
- apontar módulo provável
- gerar mensagem amigável
- manter `logs/last_error.json`

### Logging padronizado

Arquivo alterado:

```text
core/logger.py
```

Adicionado:

- lock de escrita
- `log_exception()`
- gravação em `logs/errors.log`

### GUI Hardening

Arquivos alterados:

```text
gui/chat_panel.py
gui/main_window.py
gui/self_status_panel.py
gui/memory_panel.py
gui/world_model_panel.py
gui/agency_panel.py
gui/settings_panel.py
```

Mudanças:

- chat roda pela fila `BackgroundTaskRunner`
- botão Enviar bloqueia enquanto processa
- status roda em background
- painéis capturam erro com mensagem amigável
- settings usam checkboxes
- settings sensíveis pedem confirmação

## 5. Riscos restantes

- Ainda existe uma única instância `Athena` compartilhada pela GUI. O banco está protegido, mas alguns estados pendentes em memória (`pending_world_extraction`, `pending_plan`, etc.) ainda são atributos mutáveis do Orchestrator.
- A fila de background reduz concorrência na GUI, mas o terminal ainda pode ser usado de forma concorrente se alguém instanciar múltiplas threads manualmente.
- A GUI ainda é simples e não possui cancelamento visual de tarefa longa.
- O teste real de 1 hora não foi executado neste ambiente.
- A janela real não foi aberta neste ambiente porque `customtkinter` não está instalado aqui, embora `app.py` trate a ausência corretamente.

## 6. Próximos riscos arquiteturais

- Separar estado conversacional pendente por sessão.
- Criar migrações explícitas em vez de concentrar tudo em `create_tables()`.
- Criar camada formal de repositórios para reduzir uso direto de `MemoryDB` pelos painéis.
- Criar monitor de saúde periódico para LLM, voz, SQLite e Git.
- Adicionar testes automatizados reais para GUI usando mocks.

## 7. Preparação para V13

A V12.1 prepara a V13 porque:

- estabiliza a GUI
- reduz risco de crash por thread
- introduz background tasks
- transforma erro em objeto observável pela Athena
- permite que futuras ações longas rodem sem travar a interface

## 8. Testes executados nesta entrega

Executados neste ambiente:

```bash
python -m py_compile $(find . -name '*.py')
python main.py
python inspect_memory.py
python app.py
```

Também foi executado teste concorrente com 20 threads chamando `Athena.chat()` na mesma instância.

Resultado:

```text
20 respostas
0 exceções
0 ocorrências do erro SQLite objects created in a thread
```

## 9. Limitação de teste local

`customtkinter` não está instalado neste ambiente, então `python app.py` não abre a janela aqui. O comportamento de fallback foi validado:

```text
Não consegui iniciar a interface desktop da Athena.
Dependência provável ausente: customtkinter.
Instale com: pip install customtkinter
```

## 10. Critério de robustez

A V12.1 não adiciona novas capacidades cognitivas. Ela endurece a base para que Athena Desktop deixe de parecer um protótipo frágil e comece a operar como aplicação real.

## 11. Observação sobre fallback operacional de erro

Foi adicionado um fallback local mínimo para perguntas sobre o **último erro registrado** quando a LLM estiver indisponível.

Esse fallback reconhece apenas intenção operacional de diagnóstico e não cria conhecimento, não grava memória permanente e não interpreta domínios do usuário. Ele existe para garantir que, mesmo com Ollama offline, Athena consiga responder perguntas como:

- O que aconteceu com o erro?
- Onde devo corrigir?
- Esse erro é grave?

Risco arquitetural: apesar de não ser um parser cognitivo, ainda é uma lógica local baseada em marcadores textuais de diagnóstico. Deve ser migrada futuramente para intenção estrutural via LLM quando houver modo offline estruturado melhor.
