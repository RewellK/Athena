# Auditoria — presença local, LLM e aprendizagem

## Base e escopo

Base: GitHub `RewellK/Athena`, `f4af38f` (main consultada em 19/10/2026). O usuário autorizou a versão atual, que já contém V12.9/V13-pre. Não houve acesso ao ZIP V12.4; não se afirma equivalência binária com ele. Os arquivos sincronizados da pasta `sources/` e o pacote Python `sources/` do repositório foram preservados sem edição.

Foram lidos: histórico Git, contexto recuperado da conversa “Projeto Athena core”, README, auditorias e documentos de fundação/Version X/presença. A conversa recuperada é limitada ao conteúdo disponibilizado pelo conector; não se afirma ter lido anexos ausentes ou texto truncado.

## Problemas encontrados e mudanças

1. **Ollama sem controle de carga:** antes enviava modelo/prompt e aguardava até 30 segundos por chamada. Agora há contexto/saída limitados, thinking desligado, retenção configurável, JSON na interpretação, métricas de modelo real e um orçamento compartilhado entre chamadas do turno (24 s na configuração entregue).
2. **Falha em cascata:** antes cada órgão podia repetir a espera. Agora há intervalo de recuperação e nenhum retry de inferência após timeout. Modelo ausente/incompatibilidade/memória rejeitada podem usar um fallback configurado.
3. **Diagnóstico superficial:** antes bastava `/api/tags` responder para declarar LLM ativa. Agora precisa existir um modelo configurado. `doctor.py --smoke` mede uma geração real separadamente; presença em tags ainda não prova inferência.
4. **Rede:** integração aceita apenas loopback HTTP e ignora proxies. Não inicia servidor público nem baixa modelos em runtime. Configurações remotas anteriores são rejeitadas intencionalmente.
5. **Intenção:** strings como `"false"` não são tratadas como autorização booleana verdadeira. No modo padrão, frases gerais não passam pelo catálogo legado de identidade/conversa. Comandos e aprovações continuam locais; fallback legado continua disponível em falhas.
6. **Aprendizagem linguística:** exemplos revisados alimentam a interpretação como contexto. Candidatos não confirmados não têm autoridade. A persistência já existente de aprendizagem supervisionada foi preservada.
7. **Contexto entre reinícios:** até 40 mensagens recentes, por 24 horas, em tabela SQLite separada de fatos confirmados. Não muda a política dos outros logs/stores.
8. **Residente:** processo local sem listener, LLM de fundo ou ações externas. Cede propriedade do núcleo à GUI/CLI, recarrega stores ao retomar e trata SIGTERM. Serviços não são instalados automaticamente.
9. **Loop:** exceção isolada deixa de matar silenciosamente a thread; falhas em três ciclos consecutivos entram em modo seguro. Reinício recupera snapshot ativo de um processo encerrado e preserva modo seguro.
10. **Encerramento:** filas de background são encerradas antes de fechar o banco nas entradas oficiais.
11. **ASL:** fonte ausente na base; agora existe uma DSL declarativa opcional para definições/relações, com validação e confirmação do hash para escritas. Não há executor geral ou automodificação.
12. **Self-model:** declara escopo real de ASL e residente, incluindo ausência de percepção ambiente/programação geral.

## Preservado

`python main.py`, `python app.py`, SQLite, bootstrap incremental, identidade, Self Model, World Model, objetivos, reflexão, fontes/evidência/clima, voz opcional, Git somente leitura, aprendizagem supervisionada e banco existente. A voz padrão do pacote passa a desligada/macOS local; provedores existentes continuam disponíveis por configuração.

## Verificação

- Base: 102 testes passaram antes das alterações.
- Suite ampliada: resultado final registrado abaixo.
- Compilação de fontes Python e `git diff --check`.
- Plist gerado passou em `plutil -lint`; LaunchAgent não instalado/ativado no computador.
- Integração em diretório temporário: residente inicia; CLI offline obtém núcleo; residente retoma; SIGTERM salva stopped; `--once` reinicia sem erro.
- `inspect_memory.py` executado sem erro.
- `app.py` executado: fallback de dependência ausente verificado (`customtkinter` não instalado). Janela real não validada visualmente.
- Bootstrap idempotente e aprendizagem de longo prazo continuam cobertos pelos testes existentes.

## Limites e riscos restantes

- Não há comprovação de AGI/generalidade ampla, paridade Muse ou programação autônoma.
- SQLite é o banco próprio de dados; Athena não implementa um novo motor de banco.
- ASL opera a tabela genérica de relações e definições; não espelha automaticamente o World Model. Flag antiga de execução semântica continua desligada.
- Interpretação LLM ainda pode errar intenção/alvo; confiança é declaração do modelo. O Core valida operações, mas testes finitos não garantem segurança universal.
- Heurísticas locais legadas continuam em vários órgãos e no fallback offline. Generalização depende do modelo e de exemplos revisados; isso não altera pesos.
- Não existe integração nova de e-mail/calendário, escuta ambiente, navegação autônoma, autoedição, auto-Git ou publicação pública.
- Serviço por usuário roda enquanto houver sessão e computador acordado; não há processamento durante repouso/desligamento.
- Coordenação vale para entradas oficiais; scripts externos criando Athena diretamente podem ignorar as leases.
- Aprovação ASL não autentica o usuário contra processos locais com a mesma conta; quem acessa o banco já pode alterá-lo.
- Timeout cliente não garante cancelamento imediato no Ollama; carga ou inicialização a frio podem exceder expectativa de interação. Não há meta de latência prometida.
- Logs legados/residente não têm rotação automática; não são criptografados. Contexto TTL não apaga cópias em outros stores, backups ou logs.
- Nenhum dado de usuário, banco, log ou peso de modelo entra no ZIP de código.

## Correção adicional de agência: execução versus aprovação

A auditoria encontrou `ActionEngine.execute_approved_plan()` marcando ações como executadas sem executar ferramenta externa. Corrigido: aprovação não grava execução, não incrementa sucesso de ferramenta e a resposta declara ausência de executor externo. Adicionado executor local separado para notas, lembretes e backups, com fila SQLite, estados, artefato e hash verificável. O residente executa tarefas vencidas mesmo com LLM indisponível. Notificação macOS é opcional; arquivo de caixa local continua como evidência de entrega local. Não equivale a entrega vista pelo usuário.

Essa extensão torna obsoleta qualquer leitura de “não há executor” como ausência de toda ação: existem agora três ferramentas concretas locais. Os demais planos/executores externos continuam limitados como descrito acima. Não há tarefas recorrentes automáticas, controle geral do computador ou ajuste dos pesos da LLM.


## Escopo da revisão e modelo escolhido

Varredura dos 203 arquivos Python originais (23.777 linhas), compilação da árvore, busca de subprocessos/rede/execução dinâmica, leitura manual de fluxos críticos e revisão das auditorias/documentos V12/V13-pre. Isso não é prova formal nem revisão manual linha a linha de toda a árvore. O histórico completo do Git está disponível localmente; o conteúdo de conversa recuperado continua limitado pelo conector.

Qwen3.5 2B e 0.8B foram efetivamente baixados/executados. Não foram promovidos ao padrão por erros nos probes e latência. O padrão final é Qwen2.5 3B com fallback configurável vazio. Os probes isolados com o prompt corrigido acertaram os quatro casos de identidade própria, usuário, entidade e clima externo; uma referência ambígua produziu unknown e é encaminhada ao esclarecimento. Ver `docs/LOCAL_MODELS.md` para tempos, parâmetros e limites dessa amostra. Os primeiros testes que falharam não foram contabilizados como sucesso.

O caminho de interpretação agora usa a API de chat com papéis separados. A resposta mínima do modelo contém intent/target/target_type/confidence; o Core deriva e devolve o contrato estrutural completo. Canonicalização de target_type para intenções de identidade é validação estrutural, sem interpretação por palavras da mensagem.

## Backend de habilidades

Adicionado backend SQLite para propor, verificar, ativar e executar receitas locais. A verificação executa de verdade em área temporária e não altera tarefas reais. Ativação automática só ocorre sob política explícita do Core e para composição de ferramentas existentes, de até cinco passos. Operações fora dessa lista são recusadas. Receitas persistem e executam sem modelo depois de salvas. Trata-se de aprendizagem procedural restrita; não há programação geral/autocriação de conectores/ajuste de pesos. Detalhes em `docs/SKILL_BACKEND.md`.

## Refatoração de memória

Curta e média agora têm arquivo, última observação e índices de prazo; recorrência atualiza o registro em vez de deixá-lo expirar sem renovação. Consolidação preserva o texto original e registra origem em `memory_evidence`, sem transformar contagem de palavras em conhecimento. A expiração arquiva, não exclui. Longa preserva fatos e ganha proveniência na promoção intermediária. Índice FTS5 opcional e busca lexical alternativa permitem recuperar contexto sem LLM. Testes cobrem esquema antigo, migração repetida, ausência de perda de dados, pesquisa e preservação de fatos longos. Leia `docs/MEMORY_LIFECYCLE.md` para diferenças entre candidatos e fatos e para políticas dos outros stores.

O classificador é especializado e pode selecionar `ollamaIntentModel`. Os pesos continuam compartilhados por padrão para evitar consumo desnecessário; outro modelo pode ser configurado depois de avaliação. A distinção tarefa/habilidade é uma decisão da interpretação estruturada, com validação por operações reais no Core.

## Estado de entrega — prévia, com bloqueios de aceitação

125 testes unitários passaram na árvore final, além de compilação, diff sem erro de whitespace, plist válido e teste de handoff residente/CLI/restart/SIGTERM em diretório temporário. As alterações de memória e habilidades não foram validadas por um piloto diário com a GUI; customtkinter continua ausente neste ambiente.

Os testes com LLM real não passaram integralmente. No Core completo, Qwen2.5 3B ainda excedeu 22 s no primeiro pedido de nota em um cenário frio. Com Qwen3.5 0.8B e a segunda análise de relevância removida, uma nota foi efetivamente criada e verificada em 6,52 s, e pessoa desconhecida/clima/ambiguidade tiveram respostas adequadas; porém “Quem sou eu?” ainda foi confundido com identidade da Athena. Por isso 0.8B não foi promovido ao padrão. Outros cenários anteriores exibiram rótulos incorretos e timeouts, conforme descrito acima.

O padrão conservador permanece Qwen2.5 3B, mas não há certificação de prontidão conversacional geral, nem garantia de latência de ponta a ponta. `scripts/model_eval.py` permite repetir probes locais; precisa ser complementado por tarefas com histórico e efeito real. Passar probes isolados não encerra o gate.

Esta entrega é uma prévia de implementação para revisão, não V13 final ou cumprimento completo da visão JARVIS. O serviço automático não foi instalado. Nenhum código OpenJarvis foi incorporado ou instalado nesta prévia; houve leitura/comparação documentada em `docs/OPENJARVIS_COMPARISON.md`.
