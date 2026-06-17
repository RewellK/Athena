# LocationManager

`LocationManager` administra localização do usuário como dado sensível.

Ele permite:

- salvar localização padrão quando o usuário autoriza explicitamente;
- diferenciar cidade de coordenadas;
- consultar a localização salva;
- apagar a localização;
- registrar negação de consentimento;
- impedir que clima invente latitude/longitude.

Campos principais:

- `city`
- `state`
- `country`
- `latitude`
- `longitude`
- `precision`: `city`, `coordinates` ou `unknown`
- `source`: `user_provided`, `settings`, `system_permission`, `geocoder` ou `manual_test`
- `consent_status`: `granted`, `not_requested` ou `denied`

Na V12.9, cidade sem coordenadas não aciona Open-Meteo. Nesse caso, Athena sugere uma proposta de módulo `GeocodingConnector`.

Comandos locais:

- `minha localização é São Paulo, SP`
- `use São Paulo, SP como minha localização padrão`
- `qual localização você tem salva?`
- `apague minha localização`
- `não quero salvar minha localização`
- `por que você precisa da minha localização?`

Nenhum desses comandos precisa de LLM.
