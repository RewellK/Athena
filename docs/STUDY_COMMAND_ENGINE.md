# StudyCommandEngine

`StudyCommandEngine` liga comandos de estudo ao `DailyCognitiveReview` e ao `LearningReportEngine`.

`Athena, comando estudar.` processa o buffer diario.

`Athena, o que você achou interessante?` mostra o relatorio local do estudo.

## Garantias

- nao transforma buffer em memoria permanente;
- nao promove informacao sensivel;
- nao depende de LLM para gerar relatorio local;
- nao confunde fala observada com verdade confirmada.
