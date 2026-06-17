# Linguistic Learning Platform

A plataforma linguística da Athena guarda exemplos de treino e padrões confirmados para reduzir dependência futura da LLM.

Fluxo:

1. Usuário fala.
2. Athena gera `SemanticFrame` local quando possível.
3. Reflection ou LLMTeacher pode sugerir correção.
4. A sugestão vira `TrainingExample` candidato.
5. Rewell aprova, rejeita ou corrige.
6. Exemplo aprovado vira `SemanticPattern` local.
7. Mensagens parecidas passam a usar padrão local sem LLM.

Fontes de exemplos:

- correção humana;
- `ReflectionEvent`;
- `LLMTeacherInsight`;
- teste falho;
- conversa bem-sucedida;
- seed manual.

Estados:

- `candidate`;
- `pending_human_review`;
- `confirmed`;
- `rejected`;
- `converted_to_pattern`;
- `stale`.

spaCy e Qwen são professores/percepções auxiliares. A verdade final é validação local, evidência, memória ou aprovação humana.
