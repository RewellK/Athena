# SemanticFrame

`SemanticFrame` é a representação local de sujeito, verbo, objeto e contexto usada para preparar a Athena para aprendizado linguístico sem transformar Qwen/spaCy no cérebro.

Campos principais:

- `subject`: quem executa ou é descrito.
- `verb`: relação verbal percebida.
- `object`: complemento.
- `intent`: intenção cognitiva provável.
- `target`: alvo resolvido.
- `relation_type`: relação estrutural quando houver confiança.
- `domain`: domínio externo, como `weather`.
- `required_inputs`: dados faltantes para pesquisa.
- `source` e `interpretation_source`: de onde veio a interpretação.
- `requires_validation`: quando o frame ainda precisa de revisão.

O extrator local funciona sem Qwen e sem spaCy. spaCy pode ser usado como órgão opcional de percepção sintática via `OptionalSpacyAnalyzer`; se não estiver instalado, o resultado registra indisponibilidade e o fluxo local continua.

LLM/Qwen pode sugerir frames, mas a sugestão entra como candidato de treino. Ela não vira padrão confirmado sem validação humana ou teste.
