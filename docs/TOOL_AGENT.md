# Agente local com execução verificada

Novo fluxo experimental: `toolAgentEnabled=true` nas configurações.
Mantém `python main.py`, `python app.py` e o núcleo persistente existente.
`false` restaura o roteador anterior. Comandos iniciados por `/` continuam no fluxo anterior.

A LLM local escolhe ferramentas nativas do Ollama; o Core valida argumentos,
executa ferramentas registradas e salva o histórico em `agent_trace` no SQLite.
São permitidas notas, lembretes com horário e fuso, backup SQLite verificado,
consulta/gravação de definições por pedido explícito e habilidades locais limitadas.
Habilidades novas continuam restritas às composições verificáveis de ferramentas existentes.

Uma ação concluída retorna comprovante do Core, com ID, estado, caminho e hash
quando aplicável. Não exige outra chamada de LLM para anunciar o sucesso.
Repetições idênticas no mesmo turno reutilizam o resultado; turnos distintos são
pedidos distintos e podem criar outra nota. São no máximo três etapas e quatro
chamadas de ferramenta por etapa. O orçamento de tempo é compartilhado.

Não há instalação de código gerado, shell, acesso público ou ferramentas externas
neste agente. O processo residente executa tarefas já agendadas sem manter a LLM
ocupada continuamente. Computador suspenso não executa tarefas; ao retomar, o
residente processa pendências. Não há paridade com o JARVIS ficcional.

Implementação própria inspirada na arquitetura de ferramentas/observações do
OpenJarvis. O framework OpenJarvis não foi instalado nem incorporado como dependência.
A memória de definições anterior é preservada; gravações neste fluxo também têm
pedido e resultado registrados no histórico do agente. A recuperação semântica
ampla e aprendizagem de código novo permanecem limitações.

## Validação desta revisão

No Mac Intel com 16 GB e Qwen2.5:3b via Ollama CPU:
- nota em arquivo, com hash do conteúdo: aproximadamente 3 segundos com modelo aquecido;
- identidade do usuário: resolvida como Rewell na rodada final, com variação gramatical;
- preferência gravada por pedido explícito: aproximadamente 3 segundos;
- após fechar o Core, apagar somente o histórico recente e abrir novamente, a preferência
  foi recuperada do SQLite e respondida corretamente pelo modelo.

O contexto carrega até oito fatos recentes deste agente; fatos antigos continuam
no SQLite/definições e podem exigir consulta explícita por assunto. Não é recuperação
semântica universal. O teste de reinício foi feito em cópia temporária, sem tocar
na memória pessoal. Estes são testes pontuais, não garantia de acerto em toda linguagem.

A escolha de ferramentas continua probabilística. O fluxo antigo está disponível
para reversão. O modo novo ainda não integra todas as rotas especializadas antigas
(por exemplo, clima e pesquisa); os módulos e os dados foram preservados.
