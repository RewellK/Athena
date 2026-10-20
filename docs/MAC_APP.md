# Athena como aplicativo do Mac

O aplicativo incorpora Python 3.12 e as dependências. Janela, residente e ícone
de estado usam identificadores separados para que o Finder abra a janela sem
confundi-la com um processo de fundo. Não precisa abrir o Terminal
para usar. O Ollama é instalado separadamente; quando disponível neste Mac, o
aplicativo pode iniciar seu servidor exclusivamente em 127.0.0.1:11434 se estiver
parado. Modelos de linguagem continuam no cache local do Ollama.

## Uso cotidiano

- Abra Athena pelo ícone na Mesa ou em `~/Applications/Athena.app`.
- O ícone `◉ A` na barra superior mostra estado e permite abrir a janela, pausar
  escuta, parar voz, pausar Athena e retomar.
- Fechar a janela devolve o trabalho ao serviço residente. O serviço inicia no login.
- O Mac precisa estar ligado e acordado. Não foi desativada a suspensão do sistema.
- A janela tem conversa, tarefas, memória, presença e o painel Aprender.

## Voz e presença

A saída usa Luciana do macOS. `Falar` grava um trecho e permite revisar/enviar.
A escuta ambiente é ativada pelo botão visível; o macOS pode pedir autorização de
microfone. Esse modo processa áudio localmente, em trechos limitados, sem arquivo
permanente de áudio. Pessoas próximas precisam saber que a escuta está ativa.

O modo ambiente pode aprender observações, responder com base na memória, conversar
quando claramente dirigido à Athena e colocar pedidos locais na fila. Ainda pode
errar a transcrição ou o momento de responder. A inferência em CPU tem latência.

Na aba Presença, cada participante pode cadastrar a própria voz: informar nome,
concordar e gravar três amostras de seis segundos. Apenas vetores numéricos são
persistidos, com opção de remoção. O modelo CAMPPlus usa CPU e tem cerca de 30 MB.
A comparação admite desconhecido; não é autenticação. A interrupção por voz durante
fala depende da comparação de um falante cadastrado e não é um sistema completo de
cancelamento de eco. O botão/menu Parar voz funciona independentemente disso.

## Aprendizado

Fatos comuns afirmados em conversa podem ser guardados sem comando especial.
Correções atualizam a mesma propriedade, preservando versões anteriores. O índice
SQLite FTS5 permite recuperar fatos antigos; há fallback para SQLite sem FTS5.
Observações do ambiente ficam separadas e são qualificadas como não confirmadas.

Procedimentos derivados de execuções podem ser reutilizados e versionados. O painel
Aprender reúne dificuldades reais, permite revisar experiências com a LLM e apresenta
uma proposta com justificativa. Variantes de procedimentos são testadas isoladamente
antes de aprovação e aplicação. Revisões periódicas geram aviso quando há dificuldades
recorrentes, sem chamada contínua de LLM.

Propostas de código/configuração são exportadas para investigação. A exportação não
é uma mudança implementada. Não há integração ativa com Claude/Codex para modificar
livremente o programa, nem treino de pesos nesta versão.

## Dados e reversão

Memória e configurações: `~/Library/Application Support/Athena`.
Documentos/modelos de voz: `.athena_workspace` dentro dessa pasta.
Logs: `logs/application.log` e `logs/resident.*.log`.
A instalação anterior permanece preservada. Um apontador local ignorado pelo Git
permite que `python main.py` e `python app.py` usem a nova pasta de dados.
Dados pessoais, perfis de voz e modelos baixados não são enviados ao GitHub.

A opção de presença pode ser desligada na aba Presença, sem apagar dados.
Nesta versão, abrir novamente o aplicativo reativa o residente. Para uma pausa
persistente de atividades, use Pausar Athena no menu; o estado de pausa é preservado.
Para restaurar a instalação anterior, primeiro feche a janela e pare o serviço;
preserve a pasta de dados nova antes de usar a cópia anterior.

## Compilação e distribuição

```bash
venv/bin/python -m pip install -r requirements-build.txt
venv/bin/python scripts/build_macos.py
venv/bin/python scripts/install_macos_app.py --migrate-from "$PWD" --enable-voice
```

O script de build exige o modelo público CAMPPlus preparado no local documentado em
`voice/speakers.py` e ferramentas Swift do macOS. A compilação é Intel x86_64 para o
Mac validado. Outros sistemas/arquiteturas precisam de compilação e validação próprias.
A assinatura é local (ad hoc); o aplicativo não foi notarizado pela Apple.
