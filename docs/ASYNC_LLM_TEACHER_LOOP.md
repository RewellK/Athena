# Async LLM Teacher Loop

`AsyncLlmTeacherLoop` é uma professora auxiliar opcional.

Estado antes desta etapa:

- já havia `BackgroundTaskRunner`;
- já havia `AsyncExternalResearchWorker`;
- já havia `ReflectionEngine.observe_turn`;
- ainda não havia um loop específico para Qwen/LLM analisar turnos e salvar aprendizados candidatos.

Estado atual:

- `AsyncLlmTeacherLoop` recebe turnos após a resposta;
- quando habilitado, pode usar Qwen/LLM em background;
- gera `LlmTeacherInsight`;
- cria `TrainingExample` candidato;
- cria `SelfInsight` candidato;
- pode sugerir `ResearchStrategy` candidata;
- nunca confirma aprendizado sozinho.

Por padrão, `asyncLlmTeacherEnabled` fica `false` para preservar latência. Quando ligado, o loop usa background runner se disponível. Falha do teacher loop não quebra `Athena.chat()`.

O objetivo é que a LLM ensine padrões e estratégias que depois a Athena reutiliza localmente.
