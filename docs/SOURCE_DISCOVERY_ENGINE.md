# Source Discovery Engine

## Objetivo

O `SourceDiscoveryEngine` permite que Athena responda melhor quando ainda não possui uma fonte externa configurada.

Resposta antiga:

“Não tenho ferramenta configurada.”

Resposta V12.8:

“Não sei consultar isso ainda. Encontrei uma possível fonte. Posso adicioná-la como candidata?”

## Regra de aprovação

Uma fonte descoberta é apenas uma candidata.

Ela precisa passar por:

1. aprovação humana para ser registrada;
2. validação segura;
3. aprovação humana para habilitação;
4. uso via `EvidenceEngine`.

## Por que isso é seguro

`SourceDiscoveryEngine` não consulta a fonte, não faz scraping e não cria evidência.

Ele só gera `SourceProposal`.

## Exemplo

Usuário:

“Quanto custa um Civic 2020?”

Athena:

“Não sei consultar veículos ainda porque não tenho uma fonte validada para esse domínio. Encontrei uma possível fonte: iCarros. Posso adicioná-la como fonte candidata para veículos?”

Se Rewell aprovar:

“Adicionei iCarros como fonte candidata para vehicles. Ela continua desativada e não será usada como evidência até passar por validação e nova aprovação humana.”

## Limites

Nesta fase, a descoberta usa catálogo local inicial por domínio.

Não há busca web automática.

Isso evita:

- demora;
- scraping inseguro;
- uso indevido de sites;
- transformar uma sugestão em verdade.
