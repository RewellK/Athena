# AUDIT V12.8 - Source Manager, Evidence Engine e Source Discovery

## Resumo executivo

A V12.8 adiciona a fundação para fontes externas seguras.

Athena agora pode:

1. reconhecer pedido de informação externa;
2. detectar domínio;
3. verificar se existe fonte habilitada;
4. sugerir uma fonte candidata quando não existe;
5. pedir aprovação humana;
6. registrar fonte como candidata/pending_validation;
7. impedir uso de fonte candidata como evidência;
8. preparar job externo assíncrono para fontes futuras validadas.

## Órgãos criados

- `SourceDiscoveryEngine`
- `SourceRegistry`
- `SourceManager`
- `SourceValidator`
- `EvidenceEngine`
- `FreshnessEngine`
- `SourceTrustEngine`
- `CredentialManager`
- `AsyncExternalResearchWorker`

## Regra preservada

Athena usa fontes externas. Fontes externas não são Athena.

Athena descobre. Athena sugere. Rewell aprova. Athena valida. Só depois Athena usa como evidência.

## SourceDiscoveryEngine

Implementado como catálogo local inicial por domínio.

Exemplo:

- `vehicles` -> iCarros;
- `weather` -> Open-Meteo;
- `news` -> GDELT;
- `finance` -> Banco Central do Brasil.

Essas fontes entram como sugestão, não como verdade.

## SourceRegistry

Registra fontes localmente.

Status suportados:

- `candidate`
- `pending_validation`
- `disabled`
- `enabled`
- `failed_validation`
- `rejected`
- `deprecated`

Fonte recém-descoberta nunca começa como `enabled`.

## EvidenceEngine

Fonte candidata não gera `EvidenceRecord`.

Só fonte `enabled` + `validation_status=passed` pode gerar evidência factual.

## AsyncExternalResearchWorker

Implementado como fila local simples.

Não há thread complexa nesta fase.

O worker cria jobs rapidamente e pode processar um job com `process_pending_once()`.

## Weather / News

Clima e notícias ainda não têm conector real habilitado.

Decisão: adiado de propósito.

Motivo:

- evitar dependência de internet real em teste;
- evitar scraping inseguro;
- evitar fonte não validada virando resposta factual.

## UX implementada

Sem fonte:

“Não sei consultar veículos ainda porque não tenho uma fonte validada para esse domínio. Encontrei uma possível fonte: iCarros. Posso adicioná-la como fonte candidata para veículos?”

Após aprovação:

“Adicionei iCarros como fonte candidata... Ela continua desativada e não será usada como evidência até passar por validação e nova aprovação humana.”

## Performance

O fluxo sem fonte é local.

Não chama LLM.

Não chama internet.

Não bloqueia GUI com pesquisa externa.

## Riscos restantes

- Falta conector real de clima com Open-Meteo.
- Falta validação real de termos/API.
- Falta GUI para segunda mensagem assíncrona.
- Falta fluxo explícito de habilitação depois de validação humana.
- Falta persistência mais robusta fora de `logs/` para fontes aprovadas em ambiente de produção.

## Próximos passos

1. Criar fluxo humano para validar fonte.
2. Criar habilitação humana separada de fonte validada.
3. Implementar Open-Meteo com mock HTTP nos testes.
4. Adicionar localização padrão com aprovação do usuário.
5. Criar UI de fontes candidatas/habilitadas.
6. Criar relatório “quais fontes você conhece?”.
