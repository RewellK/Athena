# Source Manager V12.8

## Papel cognitivo

O `SourceManager` é o órgão que coordena fontes externas. Ele não é a Athena inteira e não substitui Memory, World Model, Reasoning ou Reflection.

Regra central:

Athena descobre. Athena sugere. Rewell aprova. Athena valida. Só depois Athena usa como evidência.

## Fluxo implementado

Quando o usuário pede informação externa:

1. `CognitiveControlEngine` roteia como `external_information`.
2. `SourceManager` detecta o domínio.
3. `SourceRegistry` verifica se há fonte `enabled`.
4. Se não houver, `SourceDiscoveryEngine` sugere uma `SourceProposal`.
5. Athena pede aprovação humana.
6. Se aprovado, a fonte vira registro local `candidate`/`pending_validation`.
7. A fonte continua desativada.
8. Ela não pode gerar `EvidenceRecord` até validação passar e nova habilitação humana.

## Domínios iniciais

- `weather`
- `news`
- `vehicles`
- `finance`
- `sports`
- `places`
- `documentation`
- `general_web`
- `unknown_external`

## Status de fonte

- `candidate`
- `pending_validation`
- `disabled`
- `enabled`
- `failed_validation`
- `rejected`
- `deprecated`

Fontes descobertas nunca começam como `enabled`.

## SourceDiscoveryEngine

`SourceDiscoveryEngine` sugere fontes candidatas por domínio.

Exemplos iniciais:

- clima: Open-Meteo;
- notícias: GDELT;
- veículos: iCarros;
- finanças: Banco Central do Brasil.

Essas sugestões não significam confiança. Elas apenas criam uma hipótese de fonte que precisa validação.

## Validação

`SourceValidator` nesta fase é conservador. Ele não acessa internet, não faz scraping e não declara uma fonte como segura sozinho.

Resultado comum:

`pending_validation` / `needs_manual_validation`

## Performance

Quando não há fonte, a resposta é local e rápida.

Quando houver fonte validada no futuro, `AsyncExternalResearchWorker` permitirá criar job e responder imediatamente:

“Vou pesquisar clima em uma fonte configurada, já te respondo.”

Nesta fase, o worker existe como fila local com `process_pending_once()`, sem thread complexa.

## Segurança

Athena não:

- ativa fonte automaticamente;
- usa fonte candidata como evidência;
- salva API key no código;
- faz scraping agressivo;
- inventa clima, notícia, preço ou cotação;
- transforma Qwen em fonte factual.

## Onde ficam os dados locais

Por padrão:

- `logs/source_registry.json`
- `logs/evidence_records.jsonl`

Esses arquivos são runtime/local artifacts e ficam fora do Git.
