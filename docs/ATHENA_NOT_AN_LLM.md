# Athena Não Deve Virar Uma LLM

A Athena usa LLMs, mas LLMs não são Athena.

A LLM pode interpretar linguagem ambígua, sugerir `SemanticFrame`, criticar resposta, sugerir padrão, estratégia de pesquisa ou teste.

A LLM não pode confirmar aprendizado sozinha, substituir Memory/WorldModel, ser fonte factual externa, listar dados locais que já estão em stores ou implementar código automaticamente.

O caminho correto:

1. LLM sugere.
2. Athena salva como candidato.
3. Rewell/teste valida.
4. Athena converte em padrão, estratégia, insight ou proposta.
5. Athena reutiliza localmente sem LLM quando possível.

O objetivo é que cada uso de LLM ensine algo que fica dentro da Athena.
