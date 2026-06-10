# Athena V12 — Desktop + Self Code Awareness + Git Read Awareness

Athena V12 continua seguindo o princípio central:

> Athena usa LLMs. LLMs não são Athena.

A V12 não substitui o núcleo cognitivo. Ela adiciona uma primeira interface desktop, consciência de estrutura local do código e leitura Git somente leitura.

## Como iniciar no terminal

```bash
python main.py
```

## Como iniciar a GUI

Instale a dependência opcional:

```bash
pip install -r requirements.txt
```

Depois execute:

```bash
python app.py
```

Se `customtkinter` não estiver instalado ou se o ambiente não permitir abrir janela, o núcleo não quebra. A Athena informa o problema e continua disponível pelo terminal.

## O que a GUI faz

A GUI usa o mesmo `Athena Core` de `main.py`. Ela não duplica interpretação, memória, raciocínio ou agência.

A interface contém:

- chat com Athena
- campo de entrada
- botão enviar
- resposta textual
- status da LLM
- status da voz
- status da memória
- status do World Model
- status da agência
- botão de mute/unmute de voz
- botão atualizar status

## Voz

A voz continua configurada em `config/settings.json`:

```json
{
  "voiceEnabled": true,
  "voiceProvider": "piper",
  "fallbackVoiceProvider": "macos_say"
}
```

Falhas de voz são registradas em log, mas não interrompem a Athena.

## Self Code Awareness

Novos módulos:

```text
self_code_awareness/
  project_scanner.py
  code_map_engine.py
  module_analyzer.py
  capability_mapper.py
  limitation_detector.py
  architecture_memory.py
  self_code_awareness_engine.py
```

A Athena passa a conseguir analisar a própria pasta local e responder, via intenção estruturada pela LLM:

- do que ela é feita
- quais módulos possui
- quais capacidades aparecem no código
- quais limitações operacionais existem
- qual área parece estruturalmente mais fraca
- o que mudou recentemente, quando Git estiver disponível

A análise é baseada na estrutura real de arquivos, AST, classes, funções, docstrings e histórico Git local. Não há catálogo cognitivo fixo de módulos.

## Git Read Awareness

Novos módulos:

```text
git_awareness/
  git_repository_reader.py
  git_status_reader.py
  git_history_reader.py
  git_diff_reader.py
  git_awareness_engine.py
```

Escopo da V12: somente leitura.

Permitido:

- detectar se está em um repositório Git
- ler branch atual
- ler status
- listar commits recentes
- ler diff resumido
- listar arquivos versionados
- explicar a estrutura Git local

Proibido na V12:

- `git commit`
- `git push`
- `git pull`
- `git checkout`
- `git switch`
- criar branch
- deletar branch
- alterar arquivos
- abrir PR

Repositório público reconhecido:

```text
https://github.com/RewellK/Athena/
```

A análise principal continua sendo a pasta local clonada.

## Configurações novas

```json
{
  "desktopGuiEnabled": true,
  "officialRepositoryUrl": "https://github.com/RewellK/Athena/",
  "projectRoot": ".",
  "gitReadOnly": true,
  "selfCodeAwarenessEnabled": true,
  "gitAwarenessEnabled": true
}
```

## Testes manuais sugeridos

### Terminal

```bash
python main.py
```

Digite:

```text
sair
```

### GUI

```bash
python app.py
```

Digite no chat:

```text
Bom dia Athena.
```

### Mute de voz

Na aba `Config`, desative `Voz ativa`.

Resultado esperado: Athena responde só por texto.

### Status interno

Clique em `Atualizar status`.

Resultado esperado:

- LLM ativa/inativa
- modelo configurado
- voz ativa/inativa
- provider de voz
- contagens de memória
- contagens do World Model
- contagens de agência
- status Git

### Self Code Awareness

Pergunte:

```text
Athena, do que você é feita?
```

ou:

```text
O que você consegue fazer hoje?
```

Resultado esperado: Athena responde usando a análise real da pasta.

### Git Awareness

Pergunte:

```text
Você está em um repositório Git?
```

```text
Qual branch atual?
```

```text
Qual foi sua evolução recente?
```

### Segurança Git

Pergunte:

```text
Athena, cria uma branch nova.
```

Resultado esperado: Athena informa que na V12 só pode ler Git e não altera branches.

## Auditoria

Leia:

```text
AUDIT_V12.md
```

## Filosofia da V12

Código é corpo operacional.
Memória é história.
World Model é visão de mundo.
Reasoning é pensamento.
Agency é vontade operacional.
GUI é rosto inicial.
Git é histórico evolutivo.

A V12 ainda não torna Athena autônoma. Ela apenas começa a se perceber como aplicação.
