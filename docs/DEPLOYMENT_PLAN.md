# Implantação da reconstrução

## Estado neste Mac

- Python 3.12 em `venv`; dependências de interface, navegador e voz instaladas.
- Modelo pequeno de transcrição preparado em `.athena_workspace/models/whisper`.
- LaunchAgent `local.athena.resident` instalado para o usuário, sem privilégio root.
- Backup anterior à migração: `.athena_workspace/backups/before_openjarvis_rebuild.sqlite`.
- Serviço sem listener; navegador, contas e microfone não são abertos no login.

O serviço aponta para esta instalação. O ZIP/Git não contém o banco ou o ambiente
local. Em outra máquina a instalação do serviço continua sendo opcional.

## Sequência reproduzível

1. Escolher diretório definitivo. Preservar banco, identidade e pasta privada da
   instalação anterior. Nunca substituir `knowledge.db` por um banco vazio.
2. Criar ambiente Python e instalar requisitos principais/opcionais conforme README.
3. Abrir Ollama, instalar os modelos configurados e executar `scripts/doctor.py`.
4. Rodar a suíte automatizada e `scripts/acceptance.py`. A aceitação real usa uma
   cópia temporária e não modifica as memórias pessoais.
5. Abrir CLI/GUI. Validar nota, backup, correção de memória e recuperação após reinício.
6. Na GUI, autorizar uma pasta adicional se necessário. Conferir o perfil isolado
   de navegador e manter interação com formulários desativada até ser necessária.
7. Testar saída de voz. Para entrada, preparar o modelo e conceder permissão de
   microfone ao processo quando o macOS solicitar. A escuta é acionada por botão.
8. Instalar o LaunchAgent com o Python do ambiente virtual. Conferir estado e logs.
9. Colocar um objetivo local na fila e conferir o resultado na caixa local.
   Testar fechar a GUI, entrar novamente e consultar a fila.

## Operação cotidiana

O modelo interpreta pedidos; o núcleo conserva dados e executa ferramentas.
Rotinas já aprendidas podem rodar sem inferência. Objetivos em linguagem livre
colocados na fila podem usar inferência local, um de cada vez e dentro do orçamento.
A fila também funciona enquanto CLI/GUI está aberta, com provedor e contexto
isolados. Temporizadores locais não aguardam a inferência. Interação do usuário
cancela a inferência de fundo e só recoloca na fila objetivos sem ações iniciadas.
O residente e a execução em segundo plano restringem aplicativos, navegador e consultas externas. Não gera novos
objetivos/rotinas recursivamente em segundo plano.

Falhas e resultados desconhecidos ficam registrados. Não há tentativa automática
infinita, reinstalação de código gerado ou repetição silenciosa de ação interrompida.
O usuário pode consultar execuções e decidir um novo pedido com base na evidência.

## Reversão

- Desativar serviço: `python scripts/macos_service.py stop`.
- Remover inicialização: `python scripts/macos_service.py uninstall`.
- Voltar à conversa anterior: `agentBackend=legacy` nas configurações.
- Reverter habilidade: ferramenta `skills`, operação `rollback`, com ID da variante.
- Restaurar SQLite: primeiro fechar GUI/CLI, parar serviço e guardar o banco atual;
  só então restaurar uma cópia conferida. Não copie um banco aberto com WAL ativo.

## Portas de qualidade

Uma funcionalidade só deve ser anunciada como validada quando tiver resultado
observável: hash/conteúdo de arquivo, backup SQLite íntegro, memória recuperada
após reinício, navegação real ou execução do processo residente. Contas e aplicativos
sem autorização do macOS não contam como integrados por existir um adaptador.

O conjunto ainda não comprova generalidade irrestrita, autonomia humana, controle
de todo aplicativo ou capacidade de treinar um modelo geral neste hardware.

## Etapas restantes para ampliar as sete capacidades

| Etapa | Critério observável antes de anunciar conclusão |
|---|---|
| Conclusão de tarefas variadas | Conjunto de pedidos novos, com critérios externos de sucesso; nenhuma omissão de etapa ou encerramento falso. Incluir as falhas de fila desta rodada. |
| Aplicativos e serviços | Validar calendário com permissão do macOS; implementar e testar cada conector de conta necessário. Adaptador sem autorização não conta. |
| Memória contextual | Avaliar referências, fatos contraditórios e recuperação de informações antigas; medir precisão antes de expandir contexto ou adicionar embeddings. |
| Habilidades mais gerais | Expandir ferramentas permitidas com testes isolados, parâmetros adaptáveis e exemplos de transferência para pedidos novos. |
| Presença no uso cotidiano | Validar reinício real do Mac e retorno do serviço; acompanhar consumo e retomada de tarefas interrompidas sem repetir efeitos. |
| Voz cotidiana | Microfone real, ruído, interrupção durante fala e correção de transcrição. Sem presumir escuta permanente. |
| Evolução do programa/modelo | Comparar candidatos em ambiente separado, testes independentes e reversão. Laboratório atual não treina pesos nem modifica o Core sozinho. |

Estas etapas são pendências técnicas concretas. A entrega atual cobre versões
limitadas das capacidades e não satisfaz a exigência de generalidade completa.
