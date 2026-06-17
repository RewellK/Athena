# SelfExpansionPlanner

`SelfExpansionPlanner` é a superfície administrativa local para lacunas e propostas de módulos.

Comandos locais previstos:

- `quais módulos você acha que precisa?`;
- `quais propostas de módulo existem?`;
- `mostre lacunas de capacidade`;
- `aprovar proposta X`;
- `rejeitar proposta X`;
- `o que falta pra você conseguir fazer isso?`;
- `que órgão você precisa para responder isso?`.

Ele consulta `ModuleProposalStore` e não chama LLM para listar propostas já conhecidas.

Integrações:

- `SelfInsightEngine`: lacunas viram insights sobre limitações reais.
- `ResearchLearningEngine`: lacunas de pesquisa viram estratégias `needs_source` ou `needs_module`.
- `SourceDiscoveryEngine`: fonte candidata é distinta de proposta de módulo.
