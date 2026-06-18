# CommandPaletteEngine

`CommandPaletteEngine` interpreta comandos cognitivos e aciona orgaos locais.

Comando nao e so texto. Comando pode ativar modo, gerar relatorio, pausar runtime ou consolidar candidatos aprovados.

## Comandos implementados

- `Athena, aprender.`
- `Athena, comando aprendizagem.`
- `Athena, status aprendizagem.`
- `Athena, relatório aprendizagem.`
- `Aprovar aprendizado 1.`
- `Rejeitar aprendizado 1.`
- `Editar aprendizado 1: ...`
- `Consolidar aprovados.`
- `Athena, comando estudar.`
- `Athena, relatório do estudo.`
- `Athena, status.`
- `Athena, comando diagnóstico.`
- `Athena, comando silêncio.`
- `Athena, retomar.`

## Regra

Comandos claros usam caminho local e nao chamam LLM.

Comandos futuros ficam documentados, mas nao executam acoes perigosas.
