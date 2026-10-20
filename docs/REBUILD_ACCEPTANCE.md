# Critérios de aceitação: o que foi implementado e o que ainda falta

Esta matriz distingue infraestrutura executável de uma promessa de JARVIS completo.

| Pedido | Implementação | Limite atual |
|---|---|---|
| Resolver tarefas completas | Agente oficial OpenJarvis, etapas, observações, correção de erros, orçamento e comprovantes SQLite | Modelos pequenos podem interpretar errado ou omitir uma etapa. Plano executado não prova cumprimento de qualquer objetivo arbitrário. |
| Agir no computador | Arquivos em raízes autorizadas; navegador isolado com navegação/leitura/cliques; abertura de aplicativos; adaptador de calendário | Não controla todos os aplicativos. Calendário depende de permissão do macOS e ainda não foi validado neste ambiente. Contas externas não foram conectadas. |
| Memória útil | Conversa recente, diário operacional, fatos por sujeito/atributo, origem, versões, recuperação e correções | Busca lexical e contexto limitado; não resolve automaticamente todas as contradições ou referências possíveis. |
| Aprender habilidades | Procedimentos extraídos de execuções bem sucedidas, testados em ambiente temporário e reutilizáveis | Finito e limitado a ferramentas locais permitidas; não adquire qualquer habilidade humana nem instala código arbitrário. |
| Presença contínua | LaunchAgent instalado, fila de objetivos, lembretes e rotinas persistentes, handoff para CLI/GUI | Exige Mac ligado e sessão ativa. Objetivos precisam ser explicitamente colocados na fila; não existe vigilância irrestrita. |
| Conversa e voz confiáveis | Modelo local, memória, esclarecimentos, saída macOS, entrada Whisper e controles de interrupção | Ainda pode errar linguagem. Transcrição sintética em português foi aproximada; microfone real não foi validado. Revisão antes de enviar é padrão. |
| Melhorar a si mesma | Variantes testadas de procedimentos, comparação técnica, ativação e rollback; laboratório de dados | Não reescreve livremente o Core. Não houve treino de pesos nem demonstração de superioridade geral de uma LLM própria. |

## Verificações reais já executadas

- Executor e validador oficiais importados da revisão fixada; hashes conferidos.
- Navegador Chrome em perfil temporário: página inicial → identificação de link →
  navegação para a segunda página, com título e conteúdo conferidos.
- Interface desktop criada, incluindo controles de fala e interrupção.
- Voz macOS gerada em arquivo de áudio com duração e amostras válidas.
- Whisper pequeno baixado e transcrição local executada; resultado aproximado.
- LaunchAgent carregado e processo em estado `running`.
- SQLite anterior preservado em backup com `quick_check=ok`.

As medições de linguagem e execução mudaram durante a reconstrução. Não se deve
tratar uma rodada aprovada como garantia de todas as formulações. O teste
`scripts/acceptance.py` produz um relatório explícito de sucesso/falha para nota
com conteúdo exato, backup, habilidade e recuperação da preferência após reinício.
Resultados de modelos e limitações estão em `LOCAL_MODELS.md`.

## Rodada final de 20/10/2026

- 149 testes automatizados aprovados; importação e compilação verificadas.
- GUI atual abriu com os painéis de tarefas, memória, voz e interrupção.
- Com a Athena aberta: nota criada com conteúdo correto; lembrete em 0,43 s;
  prioridade para o usuário em 0,68 s; configurações de fundo isoladas.
- Serviço atualizado: nota e rotina executadas e verificadas; handoff em 0,17 s.
- Essas duas rodadas de continuidade não comprovaram encerramento confiável do
  objetivo pelo modelo: houve estado `needs_attention` apesar da nota criada.
  A comprovação de efeitos não foi convertida em sucesso semântico automático.
- A aceitação completa de 4B já passou em rodada anterior. A rodada final também
  passou (nota+backup 54,37 s, memória 46,25/65,56 s, recuperação 15,52 s),
  registrada em `VALIDATION_REPORT.json`; as falhas de fundo não são ocultadas.

[Referência Muse e diferenças](MUSE_REFERENCE.md). O serviço estar ativo não
significa que toda tarefa em linguagem livre será resolvida corretamente.
