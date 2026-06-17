# SelfInsightEngine

`SelfInsightEngine` transforma evidências locais em hipóteses sobre o que a Athena precisa melhorar.

Fontes aceitas:

- `ReflectionEvent`;
- `LLMTeacherInsight`;
- correção humana;
- teste falho;
- checklist V12;
- estratégia de aprendizado.

Um `SelfInsight` possui:

- tipo;
- conteúdo;
- módulo suspeito;
- ação sugerida;
- teste sugerido;
- fonte;
- status;
- confiança;
- exigência de revisão humana.

Nenhum insight vira verdade final automaticamente. A Athena pode responder “tem algo que você precisa melhorar?” consultando `SelfInsightStore` e `ReflectionStore`, sem inventar autoconhecimento.
