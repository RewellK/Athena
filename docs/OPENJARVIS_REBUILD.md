# Arquitetura reconstruída

## Base real

O executor não é uma reprodução inspirada no OpenJarvis. A pasta
`third_party/openjarvis` contém seus módulos oficiais OrchestratorAgent,
ToolExecutor, loop guard, tipos, eventos e auxiliares de segurança. A revisão é
`6e4defd33fb3332eed17be1169c4bb3a6e1a274c`; os hashes individuais e as alterações
nos inicializadores de pacote constam em `UPSTREAM.json`. Testes verificam os hashes.

A distribuição é um subconjunto explícito. Não carrega o SDK completo, descoberta
automática de plugins, telemetria, provedores de nuvem ou ferramentas irrestritas.
A política de permissões da Athena funciona em Python; não depende da política
Rust do upstream. O scanner de injeção usa o fallback Python oficial.

## Responsabilidades

- `brain/orchestrator.py`: entrada compatível e serviços cognitivos anteriores;
  encaminha a conversa normal ao backend configurado. Comandos `/` mantêm o fluxo
  anterior. Não houve exclusão do banco ou das estruturas cognitivas antigas.
- `integrations/openjarvis/adapter.py`: instancia o agente oficial, liga política,
  ferramentas, cancelamento, histórico e comprovantes.
- `engine.py`: traduz mensagens/chamadas para o transporte local Ollama existente.
- `catalog.py`: ferramentas, esquemas e validação de argumentos. Decisões por nomes
  estruturados de ferramenta são controle de execução, não regras por frases.
- `store.py`: diário persistente de execuções e etapas, gravado antes da ação.
- `memory.py`: fatos versionados por sujeito/atributo, origem e histórico de correções.
- `files.py`, `workspace.py`, `browser.py`, `computer.py`: adaptadores de efeitos reais.
- `skills.py`: procedimentos derivados de execuções, teste isolado, versões e reversão.
- `goals.py`, `routines.py`: fila de objetivos e recorrência persistente.
- `learning_lab.py`: revisão e exportação local de exemplos para treino futuro.
- `runtime/foreground_presence.py`: temporizadores locais independentes da
  inferência, fila com contexto/provedor isolados e prioridade para o usuário.

A LLM recebe identidade e memória relevante; escolhe ferramentas e observa os
resultados. OpenJarvis executa novas etapas até resposta final, limite de turnos ou
orçamento. A Athena acrescenta evidência verificável independentemente da narrativa.

## Continuidade e memória

A conversa recente continua no SQLite com limite e TTL. Objetivos, etapas e
resultados formam a memória operacional intermediária. Fatos explícitos ficam em
memória pessoal longa, com versões inativas preservadas ao corrigir uma propriedade.
Propriedades diferentes da mesma pessoa não se sobrescrevem. Recuperação atual é
lexical e usa fatos recentes; não é compreensão semântica universal de todo o banco.

As tabelas cognitivas anteriores permanecem. Definições antigas são consultáveis
pelo agente e continuam recebendo uma cópia das novas informações explícitas.
A busca também consulta camadas anteriores e relações exatas do World Model.
World Model, relações e ASL não foram reimplementados nem excluídos. A integração
completa de todas as rotas antigas permanece trabalho separado.

## Execução e recuperação

Cada chamada começa com uma etapa persistida como `running`. Resultado de ferramenta
fica separado de resposta textual. Ao reiniciar, etapas em andamento ficam
`uncertain`; não são repetidas silenciosamente. Alterações idênticas no mesmo turno
reutilizam comprovante; leituras podem ser repetidas para verificar mudanças.

Timeout de operação com efeito externo pode deixar resultado desconhecido. O
núcleo preserva essa condição e não apresenta ausência de resposta como sucesso.
A verificação semântica de conclusão ainda depende da qualidade do modelo e de
critérios específicos; `finished` significa fim do ciclo, não prova de qualquer
objetivo arbitrário do usuário.

## Aprendizado e evolução

Uma execução bem sucedida com múltiplas ferramentas locais pode ser convertida em
procedimento finito. O procedimento é reexecutado em banco/pasta temporários antes
de ativação pela política configurada. Ferramentas de aplicativos, rede e código
arbitrário não são aprendidas automaticamente como receitas.

O agente pode propor uma variante de procedimento, testá-la isoladamente, comparar
os resultados técnicos com a versão anterior e ativá-la. Rotinas pendentes passam
a usar a nova versão; rollback restaura a anterior. Isso melhora procedimentos,
não reescreve livremente o núcleo e não prova superioridade semântica geral.

Não existe instalação de Python gerado pela LLM ou autopromoção de pesos treinados.

## Planejamento estruturado padrão

Uma seleção inicial pela LLM reduz o catálogo às ferramentas pertinentes; não há
classificação por palavras do pedido. `agentPlanningMode=structured_plan` pede à LLM um plano JSON validado por esquema.
O adaptador traduz esse plano para chamadas padrão do executor oficial. Se o plano
declara conclusão após um lote de alterações e todas retornam sucesso, o núcleo
encerra com comprovantes sem outra chamada de LLM. Leituras ainda exigem
interpretação posterior. Erros retornam como observações para correção.

O modo `native_tools` mantém chamadas nativas do Ollama. Ambos passam pelas mesmas
permissões e ferramentas. Não há regras por palavras para decidir o pedido.
