# Backend de habilidades — capacidade real e limites

Athena agora tem um backend de habilidades locais no próprio Core. Ele permite aprender uma receita executável nova a partir de ferramentas implementadas, verificar se funciona e reutilizá-la sem LLM. Esse aprendizado é diferente de guardar uma frase dizendo que sabe fazer algo.

## Ciclo

1. Pedido de habilidade nova pode chegar como `skill_request` pela interpretação LLM ou pela CLI `design`.
2. O backend compara os passos com ferramentas reais permitidas: nota, lembrete em caixa local e backup SQLite.
3. Salva receita candidata no SQLite com ID e hash.
4. Executa todos os passos em banco e pasta temporários, com notificações desligadas; registra relatório.
5. Com `autonomousLocalSkillLearning=true`, uma composição válida passa à ativa sob política local registrada pelo Core. A LLM não concede essa autoridade.
6. Uma habilidade ativa é executada usando os executores locais; resultados apontam para tarefas e arquivos verificados. Não exige LLM para executar a receita já salva.

As receitas têm até cinco passos e textos delimitados. Não suportam código Python, shell, caminhos arbitrários, rede, exclusões, instalação de pacotes ou acesso a contas. Não há variáveis, ramificações ou aprendizagem de algoritmos gerais nesta versão; são composições literais reutilizáveis. Uma receita que contém texto “enviar e-mail” em uma nota só cria uma nota, nunca envia e-mail.

## Interface explícita

```bash
python scripts/skills.py design --request "Aprenda uma rotina que registre uma revisão em nota e gere backup"
python scripts/skills.py list
python scripts/skills.py verify --id ID
python scripts/skills.py run --id ID
```

Para propor JSON revisável, use `propose --file receita.json`. Se a ativação automática estiver desligada, `activate --id ID --approve HASH` exige a revisão do hash exato. Exemplo:

```json
{"name":"Revisão com backup","steps":[{"kind":"note","text":"Revisar os aprendizados do projeto"},{"kind":"backup"}]}
```

O aprendizado automático local pode ser desligado com `autonomousLocalSkillLearning=false`. `localAutonomyEnabled=false` também impede a execução pela conversa e pelo worker. Operações explícitas de CLI são decisões do operador local.

## O que significa verificar

O teste isolado confirma que esses executores criam os artefatos esperados e completam sem erro no ambiente de teste. Não prova que a receita corresponde à intenção humana nem que integrações externas funcionam. Uma proposta mal interpretada ainda pode ser uma receita tecnicamente válida; o escopo restrito mantém os efeitos em notas/caixa/backups, e a lista de habilidades permite revisão.

Composição ativa não é executada continuamente só porque foi aprendida. Ela é reutilizável por pedido explícito/API, e suas tarefas já agendadas são processadas pelo residente. A Athena ainda não cria sozinha uma agenda pessoal de objetivos nem implementa conectores inéditos em produção.

## Ferramenta ausente

Se o pedido exigir capacidade inexistente, `design` retorna `missing_tool` ou rejeita a proposta. O registro de propostas de módulos já existente continua sendo o caminho para desenvolver o conector. Criar código novo, avaliar dependências, obter credenciais e implantar um executor exige outro ciclo de engenharia em branch isolada com testes de integração. Não é vendido como habilidade já disponível.

## Prova automatizada

`tests/test_local_presence.py` cobre proposta, recusa de execução antes da ativação, teste em área temporária sem alterar tarefas reais, ativação sob política local, persistência, execução sem LLM, hash incorreto e rejeição de ferramenta inexistente.
