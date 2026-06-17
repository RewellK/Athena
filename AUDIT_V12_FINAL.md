# AUDIT V12 FINAL

## Resumo executivo

A V12 final fortalece a Athena como sistema cognitivo modular, não como wrapper de LLM. Foram adicionados órgãos locais para governança de memória, aprendizado de pesquisa, aprendizado linguístico, interface de treino, loop opcional de professora LLM e SelfInsight.

Também foram adicionados órgãos para lacunas de capacidade e propostas de módulos, permitindo que Athena diga “não tenho esse órgão ainda” e registre uma proposta segura em vez de inventar capacidade.

## Diagnóstico inicial antes das alterações

O repositório já tinha Core, MemoryDB, WorldModel, CognitiveControlEngine, ReflectionEngine, SourceManager, EvidenceEngine, SourceDiscoveryEngine, ExternalResearchWorker e WeatherOpenMeteoConnector. Também já havia `BackgroundTaskRunner`, mas não havia um `AsyncLlmTeacherLoop` dedicado. Reflection detectava falhas, mas não havia caminho explícito para transformar toda falha em exemplo de treino e insight administrável.

## Histórico V1 a V12

- V1: identidade e memória básica preservadas.
- V2: conceitos e aprendizado continuam via Memory/WorldModel.
- V3: relações consultáveis permanecem no WorldModel.
- V4: eventos e estados seguem separados de fatos persistentes.
- V5: LLM é ferramenta de interpretação/extração, não Athena.
- V6: SelfModel e voz continuam separados.
- V7: memória curta/média/longa existe e agora ganhou governança.
- V8: WorldModel continua fonte primária para fatos conhecidos.
- V8.1/V8.2: nomes próprios não foram adicionados como lógica cognitiva.
- V9: incerteza e não invenção continuam na rota externa/reflexão.
- V10: fontes externas têm metadados/frescor/evidência.
- V11: SourceRegistry/ToolRegistry impedem ferramenta inventada.
- V12: GUI continua interface; Core coordena.
- V12.8.1: clima usa Open-Meteo com evidência e teste mockado.

## Implementado nesta etapa

- `ResearchLearningEngine` e `ResearchStrategyMemory`.
- `MemoryGovernanceEngine` e `MemoryAdminEngine`.
- `CapabilityGapEngine`, `ModuleProposalEngine` e `SelfExpansionPlanner`.
- `SemanticFrameExtractor`.
- `LinguisticLearningWorkbench`.
- `LearningInterface`.
- `AsyncLlmTeacherLoop`.
- `SelfInsightEngine`.
- `OptionalSpacyAnalyzer`.
- comandos locais para exemplos, padrões, insights, fontes, estratégias e readiness.
- comandos locais para lacunas e propostas de módulos.
- script manual `tests/manual_v12_final_gauntlet.py`.

## Aprendizado Linguístico e Filosofia Cognitiva

A Athena agora pode guardar `TrainingExample`, promover exemplo aprovado para `SemanticPattern` e usar padrões locais sem LLM. Qwen/LLM pode sugerir interpretação, mas essa sugestão entra como candidato. spaCy pode enriquecer percepção sintática, mas é opcional.

## Aprender a aprender

Falhas de `ReflectionEvent` podem virar exemplos de treino e `SelfInsight`. O `AsyncLlmTeacherLoop` pode avaliar turnos em background e sugerir frame, padrão, estratégia de pesquisa, teste e estratégia de aprendizado. Tudo fica candidato até revisão humana.

## Athena não deve virar uma LLM

A Athena ainda usa LLM para interpretação, extração complexa e ensino auxiliar. Ela já responde localmente para identidade, capacidade, fontes conhecidas, WorldModel, memórias administrativas, padrões confirmados, fontes e propostas armazenadas. Aprendizados persistem em `TrainingExample`, `SemanticPattern`, `ResearchStrategy`, `SelfInsight`, `ReflectionEvent`, `ModuleProposal` e `EvidenceRecord`.

Qwen/LLM pode sugerir, mas não confirma. spaCy pode enriquecer percepção, mas é opcional. Dados locais são listados por stores locais, sem LLM.

## Lacunas de capacidade e propostas de módulos

`CapabilityGapEngine` detecta quando falta fonte, conector, validação, memória contextual ou módulo. `ModuleProposalEngine` cria uma proposta técnica com riscos, fontes necessárias, entradas, testes sugeridos e critérios de aceite. `SelfExpansionPlanner` lista/aprova/rejeita propostas localmente.

Quando o usuário pede preço de veículo sem fonte validada, Athena:

1. reconhece domínio `vehicles`;
2. não inventa preço;
3. sugere fonte candidata via SourceDiscovery;
4. cria proposta `VehiclePriceConnector`;
5. pede aprovação humana;
6. ao aprovar, registra fonte como `pending_validation` e proposta como `pending_human_review`;
7. alimenta `SelfInsightEngine` e `ResearchLearningEngine`.

Athena não implementa código, não instala dependência e não habilita fonte automaticamente.

## LLM como professora

A LLM pode sugerir, criticar e ensinar. Ela não é fonte factual, não substitui Memory/WorldModel e não confirma padrão sozinha.

## Fontes e evidência

Fonte externa factual exige `EvidenceRecord`. Fonte candidata ou pending_validation não sustenta resposta factual. Clima usa Open-Meteo quando há localização configurada; sem localização, Athena pede dados.

## Memória e pendências

A governança lista memórias pendentes/importantes, sugestões de limpeza, fontes, estratégias e insights. A política é marcar/sugerir, não apagar automaticamente.

## Revisão filosófico-arquitetural

1. A alteração aumenta autonomia cognitiva porque transforma falhas e sugestões em estruturas locais.
2. A dependência de LLM diminui no longo prazo, pois padrões e estratégias podem ser reutilizados.
3. Athena aprendeu procedimentos: transformar erro em treino, treino em padrão, fonte em estratégia.
4. O aprendizado fica em stores locais de linguagem, pesquisa e self-insight.
5. O aprendizado confirmado pode ser usado sem LLM.
6. Risco de virar wrapper existe se o teacher loop for usado sem validação; por isso tudo nasce candidato.
7. Testes cobrem exemplos, padrões, teacher loop, governança e pesquisa.
8. A alteração faz sentido fora do desktop porque a interface é API/comando local.

## Testes executados durante implementação

- `python3 -m unittest tests.test_v12_5`: passou.
- `python3 -m unittest tests.test_v12_5_1`: passou.
- `python3 -m unittest tests.test_v12_6`: passou.
- `python3 -m unittest tests.test_linguistic_learning_platform`: passou.
- `python3 -m unittest tests.test_memory_governance_engine`: passou.
- `python3 -m unittest tests.test_research_learning_engine`: passou.
- `python3 -m unittest tests.test_capability_gap_engine`: passou.
- `python3 -m unittest tests.test_source_manager`: passou.
- `python3 -m unittest tests.test_reflection_engine`: passou.
- `python3 -m unittest tests.test_evidence_engine`: passou.
- `python3 -m unittest tests.test_external_research_worker`: passou.
- `python3 -m unittest tests.test_weather_open_meteo_connector`: passou.
- `python3 -m unittest tests.test_asl_v0`: passou.
- `python3 tests/manual_sources_v12_8.py`: passou.
- `python3 tests/manual_weather_v12_8_1.py`: passou.
- `python3 tests/manual_v12_final_gauntlet.py`: passou.

## Transcript manual

O manual final está em `tests/manual_v12_final_gauntlet.py` e cobre identidade, capacidades, aprendizado de relação, pronome, clima sem localização, clima com fonte mockada/evidência, fonte de veículo candidata, fontes, estratégias, memórias, exemplos, padrões, insights e readiness V13.

Pontos observados no transcript:

- consultas conhecidas como `Quem é Fernanda?`, `me fala dela` e `O que você sabe sobre ela?` responderam via memória/WorldModel com `llm_calls=0`;
- clima sem localização não inventou previsão e gerou lacuna de contexto;
- clima com fonte mockada registrou evidência;
- pedido de preço de veículo não inventou preço, sugeriu `iCarros` e proposta `VehiclePriceConnector`;
- aprovação humana registrou a fonte como `pending_validation` e a proposta como `pending_human_review`;
- correção humana virou `TrainingExample`, depois padrão local aprovado;
- listagem de módulos, padrões, fontes e estratégias ocorreu localmente, sem LLM.

## Métricas esperadas

O manual imprime `route`, `target`, `domain`, `llm_calls`, `used_memory`, `used_world_model`, `used_source`, `used_research_strategy`, `evidence_id`, `reflection_events` e `duration_ms`.

## Adiado com justificativa

- Painel GUI visual de aprendizagem: preparado por API/comandos, mas não implementado para evitar acoplamento GUI/Core.
- spaCy real: opcional; sem instalação obrigatória.
- Teacher loop habilitado por padrão: adiado para preservar latência; o órgão existe e pode ser ativado.
- Geocoder de cidade para clima: ainda pendente.
- Deduplicação de `SelfInsight`: o transcript mostra que a mesma lacuna pode gerar mais de um insight quando vem por rota de pedido externo e reflexão. Isso não bloqueia V12, mas deve ser refinado antes de V13.

## Checklist V13-pre

- Core modular: ok.
- GUI como face, não mente: ok.
- memória governável: ok inicial.
- fontes administráveis: ok.
- evidência externa: ok.
- pesquisa procedural: ok inicial.
- aprendizado linguístico validável: ok inicial.
- async LLM teacher: preparado/opcional.
- self-insight local: ok inicial.
- presença desktop V13: não implementada.

## Conclusão

Athena está parcialmente pronta para iniciar V13-pre. A base cognitiva da V12 está sólida o bastante para avançar, desde que V13 preserve a regra: Athena usa LLMs, fontes e interfaces como órgãos auxiliares; Athena continua sendo o sistema cognitivo.
