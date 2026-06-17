# Learning Workbench

`LearningInterface` é a interface textual/API interna para administrar aprendizado validável.

Comandos locais suportados pelo Core:

- `mostre exemplos de treino pendentes`;
- `mostre padrões linguísticos aprendidos`;
- `mostre insights pendentes`;
- `o que a LLM te ensinou?`;
- `aprovar exemplo ...`;
- `rejeitar exemplo ...`;
- `aprovar insight ...`;
- `rejeitar insight ...`.

Esses comandos consultam stores locais. Eles não chamam LLM para listar dados internos.

Princípio:

LLM pode sugerir, mas Athena só aprende de modo reutilizável quando a sugestão vira exemplo, insight, estratégia ou padrão armazenado.
