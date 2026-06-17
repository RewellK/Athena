# ResearchLearningEngine

`ResearchLearningEngine` ensina a Athena a pesquisar melhor sem usar LLM como fonte factual.

Ele registra `ResearchStrategy` com:

- domínio;
- fonte preferida;
- fontes candidatas;
- entradas obrigatórias;
- exigência de evidência;
- TTL/frescor;
- origem do aprendizado;
- confiança;
- status.

Exemplos:

- clima com Open-Meteo e evidência vira estratégia `active`;
- veículos sem fonte validada vira estratégia `needs_source`;
- sugestão da LLM vira estratégia `candidate`, exigindo revisão humana.

O objetivo é procedural: Athena aprende como pesquisar, não inventa o resultado da pesquisa.
