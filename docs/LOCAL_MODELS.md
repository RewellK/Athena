# Modelos locais: escolha por execução medida

## Hardware validado

Mac Intel i7-9750H, 6 núcleos físicos, 16 GB de RAM, Ollama 0.40.4 em CPU.
No teste de `qwen3.5:4b` com contexto 3072, `/api/ps` informou **2,90 GiB** de
memória do modelo e **0 GiB** de VRAM. Isso não representa toda a memória do sistema.

Fontes oficiais consultadas em 20/10/2026:
[Qwen3.5 no Ollama](https://ollama.com/library/qwen3.5) e
[Qwen3:4b](https://ollama.com/library/qwen3:4b).

## Padrão escolhido

`qwen3.5:4b`, com fallback explícito `qwen2.5:3b` para modelo ausente/incompatível
ou falta de memória reportada pelo Ollama. Timeout não dispara outra inferência
longa em sequência. Não existe fallback para nuvem nem download automático de pesos.

A variante de 4B passou a aceitação de nota com conteúdo exato + backup +
aprendizado de procedimento + correção e recuperação de memória após reinício.
A variante de 2B foi mais rápida, mas falhou na mesma aceitação: estruturou um fato
incorretamente e deixou de aplicar a correção. Por isso 2B não é o padrão, apesar
de estar disponível como perfil experimental. Não basta um modelo responder a um
prompt simples para considerá-lo apto à agência.

Qwen2.5:3b permanece por compatibilidade; também apresentou erros de execução e
alvo em testes. O fallback não garante qualidade igual à configuração principal.
Qwen3:4b foi rejeitado nesta configuração após timeout e saída inadequada; apenas
a cópia baixada para esse teste foi removida. Llama3.3 não foi carregado, por estar
fora do orçamento apropriado ao computador descrito.

## Latência: limite ainda presente

A primeira aceitação aprovada de 4B levou cerca de 62 s para a tarefa composta
(com correção de argumentos), 31–35 s para gravações e 12 s para recordar a
preferência. Rodadas anteriores variaram e algumas falharam. A normalização de
strings de transporte e a seleção de ferramentas foram adicionadas para reduzir
repetição, mas a inferência em CPU ainda não oferece resposta instantânea.

A rodada final do mesmo teste passou com 54,37 s para nota+backup, 46,25 s
para guardar a preferência, 65,56 s para corrigi-la e 15,52 s para recuperá-la
após reinício. Esta variação confirma que a meta de respostas comuns rápidas
ainda não foi atingida neste hardware.

Os números são medições pontuais, não garantia. `scripts/acceptance.py` permite
repetir a verificação na instalação efetiva. `scripts/doctor.py` mostra modelo,
memória carregada, dependências e serviço. A GUI permite alternar os perfis.

Procedimentos já aprendidos, rotinas e comandos estruturados podem executar sem
LLM. A conversa livre e o planejamento novo precisam de interpretação pelo modelo.
Consumo de RAM, disco e energia continuam existindo mesmo sem cobrança de API.

## Aplicativo e planejamento progressivo

O aplicativo agora usa `agentToolMode=progressive`: pedidos comuns recebem um
catálogo pequeno em uma única chamada. Ferramentas de arquivos, navegador,
calendário e habilidades são abertas sob demanda por chamada estrutural. O
seletor antigo continua disponível fora desse modo. No teste de conversa com
aprendizado espontâneo e correção, a resposta após reinício levou 13,3 s; guardar
ou corrigir fatos levou cerca de 21–26 s. Ainda não é uma experiência instantânea.

## Configuração

- `ollamaModel`: modelo principal instalado.
- `ollamaFallbackModels`: lista explícita; até um fallback é tentado por chamada.
- `ollamaNumCtx=3072`, `ollamaNumPredict=192`: limites iniciais.
- `llmTimeoutSeconds=45`, `llmTurnBudgetSeconds=90`: limites, não metas de latência.
- `agentToolSelection=true`: selecionar ferramentas antes de enviar seus esquemas.
- `agentPlanningMode=structured_plan`: plano JSON convertido para o executor oficial.
- `native_tools`: alternativa de chamadas nativas, também sujeita à aceitação.

Não configure modelos grandes apenas por novidade. Antes de mudar o padrão,
compare comportamento, memória efetiva e latência com os mesmos casos.
