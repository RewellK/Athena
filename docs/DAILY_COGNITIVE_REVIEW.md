# Daily Cognitive Review

`DailyCognitiveReview` processa o `DayMemoryBuffer` quando Rewell pede estudo.

Comandos:

- `Athena, comando estudar.`
- `Athena, estudar o dia.`
- `Athena, revisar o que falamos hoje.`

O estudo:

- marca o buffer como `studying`;
- filtra ruido simples;
- cria `LearningCandidate`;
- marca o buffer como `reviewed`;
- deixa tudo aguardando revisao humana.

Frase-guia:

`Eu estudei o nosso dia. Não guardei tudo. Separei o que parece importante, descartei ruído e deixei candidatos prontos para sua revisão.`

## Buffer vs memoria

O estudo diario cria candidatos. Ele nao e a fonte final da verdade.

Mesmo que o `DayMemoryBuffer` seja descartado, memorias promovidas continuam recuperaveis em `long_term_memory`. Isso separa experiencia bruta, candidato revisavel e memoria confirmada.
