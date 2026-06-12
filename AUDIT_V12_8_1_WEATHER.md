# AUDIT V12.8.1 - Weather Open-Meteo Connector

## Resumo executivo

A V12.8.1 implementa o primeiro conector externo real da Athena: `WeatherOpenMeteoConnector`.

O conector usa Open-Meteo como fonte de clima, cria `EvidenceRecord`, respeita TTL/frescor e falha de forma honesta.

A regra central foi preservada:

Athena usa fontes externas. Fontes externas não são Athena.

## Verificação de contrato

Contrato verificado na documentação oficial da Open-Meteo:

- endpoint `/v1/forecast`;
- `latitude` e `longitude` são coordenadas obrigatórias;
- `daily` aceita variáveis como `weather_code`, `temperature_2m_max`, `temperature_2m_min` e `precipitation_probability_max`;
- `daily` exige `timezone`;
- `forecast_days` controla a janela de previsão.

## Implementado

Arquivos criados:

- `sources/connectors/__init__.py`
- `sources/connectors/weather_open_meteo.py`
- `tests/test_weather_open_meteo_connector.py`
- `tests/manual_weather_v12_8_1.py`
- `docs/WEATHER_OPEN_METEO_CONNECTOR.md`
- `AUDIT_V12_8_1_WEATHER.md`

Arquivos alterados:

- `sources/source_manager.py`
- `sources/source_registry.py`
- `sources/external_research_worker.py`
- `sources/evidence_engine.py`
- `core/settings.py`
- `config/settings.json`
- `brain/orchestrator.py`
- `reflection/reflection_engine.py`
- testes e docs relacionados.

## SourceRegistry

Quando `defaultWeatherSource=weather.open_meteo`, o `SourceManager` registra:

- `source_id=weather.open_meteo`
- `domain=weather`
- `name=Open-Meteo`
- `status=enabled`
- `validation_status=passed`
- `requires_api_key=no`
- `connector_type=weather_open_meteo`
- `trust_level=high`
- `freshness_ttl_seconds=3600`

Fontes candidatas continuam sem habilitação automática.

## Localização

Athena usa `weatherDefaultLocation`.

Sem latitude/longitude:

“Ainda não possuo uma localização padrão para clima...”

Não há geocoding nesta versão.

## EvidenceRecord

Toda resposta climática factual precisa de evidência.

O registro inclui:

- `source_id`
- `source_name`
- `domain=weather`
- `query`
- `fetched_at`
- `valid_until`
- `freshness_ttl_seconds`
- `location`
- `forecast_date`
- `result_summary`

## UX

Com fonte e localização:

“Vou pesquisar o clima, já te respondo.”

Como a GUI ainda não entrega uma segunda mensagem assíncrona automaticamente, o fluxo atual processa inline quando `externalResearchProcessInline=true`.

## Falhas

Se a fonte falhar:

“Tentei consultar a fonte de clima, mas a consulta falhou. Prefiro não inventar.”

Se faltar localização, nenhum job é criado.

## Teste manual

Resultado observado:

- sem localização: `source_status=missing_location`, `llm_calls=0`, `duration_ms=2`;
- localização mockada: `source_status=completed`, `evidence_id` presente, `llm_calls=0`, `duration_ms=3`;
- fonte falha: `source_status=source_failure`, `job_status=failed`, `llm_calls=0`, `duration_ms=3`.

## Riscos restantes

- Geocoding ainda não implementado.
- GUI ainda não mostra resultado posterior de job assíncrono.
- Teste unitário não usa internet real por segurança.
- Validação/habilitação humana completa de fontes ainda pode evoluir.

## Próximos passos

1. Adicionar geocoding Open-Meteo com mock HTTP.
2. Criar tela/estado de jobs externos na GUI.
3. Permitir configurar localização padrão pela conversa com aprovação humana.
4. Expandir mapeamento meteorológico.
5. Implementar notícias/RSS com a mesma disciplina de evidência.
