# AUDIT V12.9 RISK CLOSURE

## Resumo

A V12.9 fecha riscos finais da V12 antes da V13-pre. Ela não implementa V13, Desktop Presence, avatar ou corpo visual. O foco é consentimento de localização, deduplicação de insights/propostas, segurança do AsyncLlmTeacherLoop, settings locais preservados e gate explícito de readiness.

## Riscos Encontrados Após V12 Final

1. Clima sabia pedir localização, mas não havia órgão próprio para administrar localização do usuário.
2. Localização precisava de consentimento, consulta e apagamento local.
3. Cidade sem coordenadas poderia ficar ambígua sem geocoder.
4. `SelfInsight` podia duplicar a mesma lacuna.
5. `ModuleProposal` podia registrar propostas equivalentes repetidas.
6. O painel visual de aprendizado ainda não existe.
7. O gate dizia “parcialmente pronta”, não “agora sim”.

## Correções

- Criado `LocationManager` com `LocationStore` e `UserLocation`.
- `SourceManager` consulta `LocationManager` antes de clima.
- Cidade sem coordenadas gera `missing_geocoder` e proposta `GeocodingConnector`.
- `SelfInsightStore` agora usa `dedup_key`, `occurrence_count`, `first_seen_at`, `last_seen_at` e `related_event_ids`.
- `ModuleProposalStore` agora usa `dedup_key`, `occurrence_count`, `first_seen_at` e `last_seen_at`.
- `SelfExpansionPlanner` pode criar proposta genérica de módulo/melhoria sem implementar código.
- `LearningReviewPanel` fica registrado como proposta possível, não como GUI implementada.
- `Settings.load()` não reescreve `config/settings.json` automaticamente quando surgem defaults novos.
- Gate `v12_9_readiness` responde explicitamente se Athena está pronta para V13-pre.

## LocationManager

`LocationManager` salva localização somente com consentimento explícito. Ele distingue:

- `precision=city`: cidade/estado/país sem coordenadas;
- `precision=coordinates`: latitude/longitude disponíveis;
- `precision=unknown`: sem localização útil.

Ele responde localmente a:

- `minha localização é São Paulo, SP`;
- `use São Paulo, SP como minha localização padrão`;
- `qual localização você tem salva?`;
- `apague minha localização`;
- `não quero salvar minha localização`;
- `por que você precisa da minha localização?`.

## Como Athena Pede Localização

Quando o usuário pergunta clima sem localização:

“Para consultar o clima, preciso de uma localização. Posso usar uma cidade padrão? Se quiser salvar, diga: "use São Paulo, SP como minha localização padrão".”

Ela não inventa cidade.

## Como Athena Salva e Apaga Localização

Ao receber comando explícito, Athena salva cidade/estado como localização padrão com `consent_status=granted`. Se não houver coordenadas, ela informa que ainda não consultará Open-Meteo.

Ao receber comando de apagar, ela remove o registro local.

## Como Clima Usa Localização

Fluxo:

1. Pergunta de clima.
2. `SourceManager` pergunta ao `LocationManager`.
3. Se houver coordenadas e consentimento, consulta Open-Meteo.
4. Se houver só cidade, não consulta e propõe `GeocodingConnector`.
5. Se não houver localização, pede localização.

## Geocoder

Geocoder não foi implementado na V12.9. Ele vira proposta de módulo `GeocodingConnector`, com risco de privacidade e critério de aceite de não inventar coordenadas.

## Deduplicação de SelfInsight

Insights equivalentes usam `dedup_key`. Quando reaparecem:

- `occurrence_count` aumenta;
- `last_seen_at` atualiza;
- `related_event_ids` preserva eventos relacionados;
- se rejeitado, não volta como pendente imediatamente;
- se confirmado, recebe nova ocorrência sem duplicar.

## Deduplicação de ModuleProposal

Propostas equivalentes por título/domínio/tipo usam `dedup_key`. Quando reaparecem, a store retorna a existente e incrementa `occurrence_count`.

Exemplo: pedidos repetidos de preço de veículos reutilizam `VehiclePriceConnector`.

## Propostas Genéricas de Melhoria

Athena pode registrar uma proposta segura para qualquer melhoria que consiga classificar localmente. Exemplos:

- `GeocodingConnector`;
- `LearningReviewPanel`;
- `LegalResearchConnector`;
- fallback genérico `UnknownExternalResearchConnector`.

Ela não implementa código, não instala dependência e não ativa fonte automaticamente.

## Async Teacher Loop

O `AsyncLlmTeacherLoop` continua desativado por padrão para proteger latência. Quando ativado:

- enfileira turnos;
- consulta LLM em background ou sob processamento explícito;
- salva insight candidato;
- falhas viram candidato seguro;
- nada vira verdade sem revisão humana.

## Settings Locais

`config/settings.json` pode continuar com preferências locais como `voiceEnabled=true`. A entrega cognitiva usa defaults em `core/settings.py`. A partir da V12.9, o loader não reescreve o arquivo local automaticamente, a menos que `rewriteSettingsOnLoad=true`.

## Artefatos

Critério mantido:

- `knowledge.db` não deve ser rastreado;
- `*.db` não deve ser rastreado;
- `logs/*` não deve ser rastreado, exceto `logs/.gitkeep`;
- `__pycache__/`, `.pytest_cache/`, `.DS_Store`, `__MACOSX`, venv e `.env` não devem entrar em commit.

## Manual

`tests/manual_v12_9_risk_closure.py` cobre:

- clima sem localização;
- salvar localização;
- consultar localização salva;
- clima com cidade sem coordenadas;
- apagar localização;
- pedido de veículo repetido sem duplicar proposta;
- pesquisa jurídica sem inventar jurisprudência;
- proposta de painel de aprendizado;
- SelfInsights;
- propostas de módulo;
- gate V13-pre.

## Testes Executados

- `python3 -m unittest discover tests`: passou, 85 testes.
- `python3 -m py_compile $(find . -name '*.py')`: passou.
- `python3 inspect_memory.py`: passou.
- `git diff --check`: passou.
- `python3 tests/manual_sources_v12_8.py`: passou.
- `python3 tests/manual_weather_v12_8_1.py`: passou.
- `python3 tests/manual_v12_final_gauntlet.py`: passou.
- `python3 tests/manual_v12_9_risk_closure.py`: passou.

## Transcript V12.9 Observado

No manual V12.9, Athena:

- pediu localização para clima sem inventar cidade;
- salvou `São Paulo, SP` como localização padrão com consentimento;
- informou que a localização salva não tinha coordenadas;
- recusou consultar Open-Meteo sem coordenadas/geocoder;
- propôs e registrou `GeocodingConnector` após aprovação;
- apagou a localização;
- reutilizou `VehiclePriceConnector` com `occurrence_count=2`;
- recusou pesquisa jurídica sem fonte validada;
- criou `LearningReviewPanel` como proposta, não implementação;
- respondeu o gate: “agora sim, pronta para iniciar V13-pre”.

## Riscos Restantes

- `GeocodingConnector` ainda é proposta, não implementação.
- `LearningReviewPanel` ainda é proposta, não GUI pronta.
- A deduplicação é conservadora e pode precisar de chaves mais finas em V13.
- Localização temporária “só agora” não executa clima sem coordenadas/geocoder.

## Conclusão

Com os testes passando, a Athena fica pronta para iniciar V13-pre. A condição é manter a filosofia: Athena é o sistema cognitivo; LLMs, spaCy, fontes, geocoder e GUI são órgãos auxiliares.
