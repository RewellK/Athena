# Evidence Engine V12.8

## Papel

`EvidenceEngine` cria registros de evidência para respostas externas.

Ele diferencia:

- memória do usuário;
- World Model;
- inferência;
- hipótese de LLM;
- fonte externa validada;
- fonte candidata não verificada.

## Regra principal

Fonte candidata não gera `EvidenceRecord` confiável.

Somente uma fonte com:

- `status=enabled`;
- `enabled=true`;
- `validation_status=passed`;
- confiança mínima aceitável;

pode gerar evidência para resposta factual externa.

## EvidenceRecord

Campos principais:

- `evidence_id`
- `source_id`
- `source_name`
- `domain`
- `query`
- `fetched_at`
- `valid_until`
- `freshness_ttl_seconds`
- `confidence`
- `raw_summary`
- `location`
- `forecast_date`
- `result_summary`
- `url`
- `license_or_notes`

Na V12.8.1, respostas de clima da Open-Meteo preenchem `location`, `forecast_date` e `result_summary`.

## Fonte candidata

Fonte candidata pode gerar apenas `UnverifiedSourceNote`, não fato.

Isso permite que Athena diga:

“Tenho uma possível fonte, mas ela ainda não está validada.”

sem fingir que já sabe o dado externo.

## Frescor

`FreshnessEngine` calcula validade por domínio.

Exemplos:

- clima: TTL curto;
- notícias: TTL curto;
- finanças/cotação: TTL muito curto;
- veículos: TTL mais longo;
- documentação: TTL longo.

Evidência vencida não deve ser apresentada como atual.

Para clima, o TTL configurado é `weatherForecastTtlSeconds`, por padrão 3600 segundos.
