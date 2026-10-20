# Athena — reconstrução com OpenJarvis

Athena usa LLMs. LLMs não são Athena.

O caminho padrão de conversa e execução agora utiliza o **OrchestratorAgent e o
ToolExecutor reais do OpenJarvis**, fixados em uma revisão auditável. Athena mantém
identidade, SQLite, histórico, ferramentas, permissões, voz e presença residente.
O roteador antigo continua disponível para compatibilidade.

Esta é uma reconstrução funcional em evolução, não uma declaração de paridade
com o JARVIS ficcional. Veja a [matriz de capacidades e limitações](docs/REBUILD_ACCEPTANCE.md).

## Aplicativo do Mac

Há uma compilação `.app` com Python incorporado, ícone na Mesa e menu na barra
superior. Memória fica fora do aplicativo; fechar a janela mantém o residente.
Veja [uso, voz, dados e instalação](docs/MAC_APP.md).

## Usar neste computador

O ambiente `venv` foi preparado localmente. O modelo principal é `qwen3.5:4b`,
com fallback configurável para `qwen2.5:3b`. Abra o Ollama e execute:

```bash
venv/bin/python main.py
# interface desktop
venv/bin/python app.py
```

Experimente:

- `Crie uma nota contendo "Revisar projeto" e faça um backup da memória.`
- `Guarde que minha cor favorita é azul.`
- `Minha cor favorita agora é verde. Atualize a mesma propriedade.`
- `Liste os procedimentos que você aprendeu.`
- `Liste os arquivos da sua pasta de trabalho.`
- `Coloque na fila para executar em segundo plano: criar uma nota sobre revisar o projeto.`

O comprovante anexado pelo núcleo mostra ações realmente executadas. Uma resposta
sem ferramenta não comprova alteração no computador. Os modelos ainda podem errar
interpretação, pronomes e seleção de ferramentas; confira os resultados importantes.

Na aba **Tarefas**, coloque objetivos na fila, consulte resultados e execute
procedimentos aprendidos sem chamar a LLM. A fila continua funcionando com a
janela aberta; sua conversa tem prioridade sobre a inferência em segundo plano.

Na GUI, **Autorizar pasta de trabalho** permite escolher uma pasta adicional.
Por padrão, os arquivos ficam em `.athena_workspace`. Escritas e cópias não
sobrescrevem arquivos existentes. Navegação usa perfil isolado, separado de suas
contas; preenchimento/botões ficam desativados por padrão.

**Falar** grava seis segundos somente quando acionado e transcreve localmente.
A transcrição aparece para revisão; o envio automático é opcional em Config.
A síntese usa a voz Luciana do macOS. Ative **Voz ativa** para ouvir respostas.
**Interromper / parar voz** impede novas etapas; uma chamada já iniciada pode
precisar terminar. Não há palavra de ativação ou escuta permanente.

## Instalar em outro diretório/computador

Recomendado Python 3.11–3.13; validação também usa Python 3.12 neste Mac Intel.
O código do executor não depende do SDK completo nem de extensão Rust compilada.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# opcionais: navegador e entrada de voz
pip install -r requirements-optional.txt
ollama pull qwen3.5:4b
ollama pull qwen2.5:3b
python scripts/voice_chat.py --prepare
python scripts/doctor.py
python main.py
```

Se o Chrome não estiver instalado, instale o Chromium do Playwright com
`python -m playwright install chromium`. Os downloads requerem internet;
inferência e voz funcionam localmente depois. O ZIP não inclui modelos, ambiente
Python, banco pessoal, logs, documentos nem dados de treino.

Antes de atualizar uma instalação existente, faça backup do SQLite e da pasta de
trabalho. Os esquemas novos são aditivos; não apagam as tabelas anteriores.

## Presença contínua

Foi instalado neste Mac o LaunchAgent do usuário `local.athena.resident`.
Ele inicia no login, acompanha lembretes, rotinas verificadas e objetivos
explicitamente colocados na fila. Não abre serviço público nem mantém o microfone
ativo. Objetivos em segundo plano usam apenas ferramentas locais e inferência
limitada; não podem criar novas filas/rotinas para se perpetuar.

```bash
python scripts/macos_service.py status
python scripts/macos_service.py stop
python scripts/macos_service.py start
python scripts/macos_service.py uninstall
# instalação opcional em outra máquina, depois de escolher o diretório definitivo
python scripts/macos_service.py install
```

O residente cede o banco à GUI/CLI e retoma depois. Enquanto a janela ou CLI
está aberta, trabalhadores separados mantêm os lembretes e a fila de objetivos;
a conversa do usuário interrompe a inferência de fundo. Suspensão/desligamento pausam
execução; iniciar no login não significa executar enquanto o Mac estiver desligado.
Não mova a instalação com o serviço ativo: desinstale e reinstale no novo local.

## Testar e reverter

```bash
python -m unittest discover -s tests -q
# teste real em cópia temporária, sem tocar no banco pessoal
python scripts/acceptance.py
```

Para voltar à conversa anterior, defina `agentBackend` como `legacy` em
`config/settings.json`. `toolAgentEnabled` controla o agente experimental anterior.
Os módulos antigos de World Model, self-model, ASL, fontes e aprendizagem foram
preservados; isso não significa que todos estejam conectados à nova conversa.

[Arquitetura](docs/OPENJARVIS_REBUILD.md) · [Implantação](docs/DEPLOYMENT_PLAN.md) ·
[Modelo e medições](docs/LOCAL_MODELS.md) · [Treino local](docs/TRAINING.md) ·
[Licenças e origem](THIRD_PARTY_NOTICES.md)
