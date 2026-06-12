# Weather Open-Meteo Connector V12.8.1

## Papel

`WeatherOpenMeteoConnector` é o primeiro conector externo real da Athena.

Ele é um órgão sensorial de clima. Ele não é Athena, não decide sozinho e não vira fonte permanente de verdade sem `EvidenceRecord`.

## Contrato usado

O conector usa o endpoint:

`https://api.open-meteo.com/v1/forecast`

Contrato verificado na documentação oficial da Open-Meteo:

- `latitude` e `longitude` são coordenadas obrigatórias.
- variáveis `daily` podem incluir `weather_code`, `temperature_2m_max`, `temperature_2m_min` e `precipitation_probability_max`;
- quando `daily` é usado, `timezone` é necessário;
- `forecast_days` controla quantos dias de previsão são retornados.

## Localização

A Athena não inventa localização.

Ela usa `weatherDefaultLocation` em settings:

```json
{
  "city": "",
  "state": "",
  "country": "",
  "latitude": null,
  "longitude": null
}
```

Se latitude/longitude estiverem ausentes, a resposta é:

“Ainda não possuo uma localização padrão para clima...”

Geocoding fica para uma próxima versão.

## Fonte registrada

Quando `defaultWeatherSource` é `weather.open_meteo`, o `SourceManager` registra:

- `source_id`: `weather.open_meteo`
- `domain`: `weather`
- `name`: `Open-Meteo`
- `source_type`: `api`
- `requires_api_key`: `no`
- `supports_api`: `yes`
- `connector_type`: `weather_open_meteo`
- `status`: `enabled`
- `validation_status`: `passed`
- `trust_level`: `high`

Essa habilitação vale apenas para o conector implementado e testado. Fonte candidata descoberta por `SourceDiscoveryEngine` continua não sendo habilitada automaticamente.

## Fluxo de resposta

Com fonte e localização configuradas:

1. Athena roteia `external_information`.
2. `SourceManager` encontra `weather.open_meteo`.
3. `AsyncExternalResearchWorker` cria/processa o job.
4. `WeatherOpenMeteoConnector` retorna `WeatherResult`.
5. `EvidenceEngine` cria `EvidenceRecord`.
6. Athena responde com fonte, evidência e validade.

Como a GUI ainda não envia uma segunda mensagem automaticamente, a V12.8.1 processa inline quando `externalResearchProcessInline=true`.

## Erros

Se a API falhar, o conector propaga erro controlado. O worker marca o job como `failed`.

Athena responde:

“Tentei consultar a fonte de clima, mas a consulta falhou. Prefiro não inventar.”

## Testes

Os testes unitários usam HTTP mockado.

Eles não dependem de internet real.
