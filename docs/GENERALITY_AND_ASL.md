# Auditoria de generalidade, manifesto e linguagem própria

Foram lidos os princípios em `docs/ATHENA_NOT_AN_LLM.md`, o relatório `docs/ATHENA_VERSION_X_ARCHITECT_LEARNING_REPORT.md`, o índice de presença e as auditorias V12.4 a V13-pre. Não existe um arquivo versionado chamado manifesto; esses documentos registram a filosofia: continuidade, identidade, memória, evidência, aprendizagem gradual e autonomia governada.

## O que existe

- Python implementa os órgãos; SQLite persiste fatos, definições, relações, eventos, objetivos, ações e memória supervisionada.
- O Self Model constrói uma descrição interna a partir da identidade, configuração e contagens locais.
- `SemanticFrame` representa sujeito/verbo/objeto e contexto. `LinguisticLearningWorkbench` armazena exemplos e padrões confirmados. Isso é uma representação linguística, não um compilador de programas.
- Pesquisa usa registro de fontes/evidências e há conector meteorológico. Não implica navegação arbitrária ou acesso a qualquer informação atual.
- A agência existente propõe planos e ações sob aprovação; não equivale a execução geral no computador.

## O que estava ausente

O histórico e `AUDIT_V12_6.md` registram ASL apenas como artefato local não versionado. `test_asl_v0.py` só verificava que a opção estava desligada. Não havia parser/intérprete ASL no código versionado. Portanto a afirmação de que ela já programava em linguagem própria não era sustentada.

## Avanço: ASL 1

Agora há um intérprete pequeno, fonte versionada e testes reais. É uma linguagem declarativa em JSON para operações do banco. Não é uma linguagem de programação geral: não há loops, funções, compilação, shell, Python eval/exec, SQL livre ou alteração do código da Athena.

Operações:

| op | args | Aprovação |
|---|---|---|
| definition.get | concept | leitura |
| definition.set | concept, meaning | hash exato; não substitui definição existente |
| relation.find | source e/ou relation e/ou target | leitura |
| relation.add | source, relation, target | hash exato; repetição idempotente |

Exemplo de arquivo `relacao.json`:

```json
{"asl":"1","op":"relation.add","args":{"source":"Motor","relation":"parte_de","target":"Máquina"}}
```

```bash
python scripts/asl.py relacao.json
# Revise o programa retornado e copie seu digest:
python scripts/asl.py relacao.json --approve HASH_EXATO
```

Consultas não exigem hash. Um hash de outro programa não autoriza a escrita. Esse mecanismo é uma confirmação explícita para o operador local, não autenticação contra alguém que já tenha acesso à conta e ao banco. A LLM não recebe executor, não gera sua própria aprovação nem aciona ASL na conversa. Relações ASL usam a tabela genérica `relationships`; não criam automaticamente entidades nem espelham relações no World Model. Isso evita inventar equivalência entre schemas que têm semânticas diferentes.

## Ela já é generalista?

Ainda não há evidência suficiente para afirmar isso. Há órgãos de múltiplos domínios e linguagem natural ampla via LLM, mas roteamento e extração ainda usam padrões locais em partes do fluxo. Generalização fora desses padrões depende do modelo e da ferramenta disponível. Os testes verificam cenários definidos, persistência e governança; não demonstram capacidade geral independente de domínio.

A ASL atual amplia a capacidade de operar a memória com estrutura verificável. Não transforma Athena em AGI, agente de programação autônoma ou sistema equivalente ao Muse. Os próximos gates precisam medir tarefas novas, resolução de referências, recuperação contextual, seleção de ferramentas, falhas, aprovação e aprendizado transferível entre domínios, mantendo avaliação separada dos exemplos de treino.

## Aprendizagem aplicada ao roteamento

Nesta evolução, `conversationRoutingMode=llm_first` separa comandos administrativos da interpretação geral. Identidade, pessoas e conversa livre chegam à LLM em vez de serem decididas pelo catálogo legado de frases. Os controles de comandos e confirmação continuam locais. Se a LLM estiver indisponível ou não entender, o fallback local preserva operações existentes e sinaliza a origem nas métricas.

Exemplos revisados em `LinguisticLearningWorkbench` agora são recuperados por similaridade textual e enviados como dados à interpretação LLM. Apenas exemplos convertidos em padrão confirmado entram no contexto; sugestões não revisadas não entram. Isso permite reutilizar uma correção aprovada entre reinícios. Não altera pesos do modelo, não treina uma rede neural e não garante transferência de conhecimento para qualquer domínio. A similaridade textual serve para recuperar exemplos, não para aprovar ações nem determinar sozinha a intenção.

O modo legado segue disponível com `conversationRoutingMode=legacy` para comparação e recuperação. Os órgãos locais existentes ainda contêm heurísticas; removê-los integralmente nesta etapa apagaria capacidades. A evolução reduz sua autoridade na interpretação geral e mantém validações determinísticas no Core.

## Aprendizagem sem chamada LLM em casos conhecidos

`resolve_reviewed()` acrescenta uma memória de interpretações locais: compara a mensagem normalizada com exemplos revisados, explicitamente marcados como independentes do contexto. Só reutiliza operações de leitura (identidade, usuário, entidade e capacidades). Exemplos candidatos, dependentes de contexto ou contraditórios não são executados por esse caminho. Não há generalização presumida de pronomes ou ações a partir de semelhança textual.

Para ensinar uma interpretação local e revisá-la explicitamente:

```bash
python scripts/teach.py --utterance "Conte sobre o projeto Aurora" --intent entity_query --target Aurora --target-type entity --approve-context-free
```

Sem `--approve-context-free`, o exemplo fica candidato. Aprovar pelo Workbench sem essa marca não autoriza reutilização independente de contexto. Isso permite que um conhecimento de linguagem revisado seja reutilizado sem modelo, sem acrescentar condicionais específicas no código. Perguntas novas continuam podendo precisar da LLM; esse mecanismo não demonstra compreensão humana geral.
