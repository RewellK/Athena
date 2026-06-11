# V12.6 Readiness Report

## Athena esta pronta para V13 Desktop Presence?

Sim, com ressalvas. Athena esta pronta para iniciar V13 como camada de presenca desktop, desde que a V13 seja construida sobre o Core atual e nao substitua memoria, World Model, reasoning, relevance, cognitive control ou conversation routing por logica de GUI.

## O que deve ser corrigido antes da V13?

- Validar manualmente a GUI no desktop real usando o roteiro V12.6. O caminho `Athena.chat()` usado pela GUI ja foi validado com banco temporario em `tests/manual_conversation_v12_6.py`.
- Publicar a `main` se as credenciais GitHub locais permitirem.
- Confirmar em uso real que `Athena.command` abre a GUI no ambiente do usuario.
- Confirmar que o banco local atual nao esta corrompido usando `python3 inspect_memory.py`.

## O que pode ser deferido para V13?

- Desktop Presence.
- UI mais rica de voz/presenca.
- Botao visual de reset seguro.
- Generalizacao mais elegante de verbalizacao relacional.
- Reduzir chamadas LLM para respostas curtas como `sim` quando nao ha confirmacao pendente.
- ASL versionado e integrado de forma opcional, se ainda fizer sentido.

## ASL

`useAthenaSemanticLanguage` existe em settings e fica `false` por padrao. O repo atual nao contem fonte ASL versionada; apenas artefatos locais ignorados em `semantic_language/`.

## O que nao deve ser feito ainda?

- Reescrever a arquitetura cognitiva.
- Transformar a GUI em decisor sem passar pelo Core.
- Ativar ASL por padrao.
- Adicionar TTS online obrigatorio.
- Criar automacoes com escrita Git sem aprovacao explicita.
- Criar empacotamento DMG antes de estabilizar a experiencia local.

## O que seria perigoso adicionar agora?

- Hardcodes cognitivos de pessoas, relacoes ou sentimentos.
- Respostas inventadas para clima/noticias/precos/eventos atuais.
- Reset de banco sem backup e sem confirmacao forte.
- Voice/TTS bloqueando resposta textual.
- Fluxos que chamam LLM para toda pergunta simples ja conhecida.

## Decisao

V12.6 deixa Athena pronta para iniciar V13, mas a primeira tarefa de V13 deve ser presenca desktop sobre o Core, nao uma nova fundacao cognitiva.

## Evidencia de validacao

- `tests.test_v12_5`: OK
- `tests.test_v12_5_1`: OK
- `tests.test_v12_6`: OK
- `tests.test_asl_v0`: OK
- `py_compile`: OK
- `git diff --check`: OK
- `inspect_memory.py`: OK
- `tests/manual_conversation_v12_6.py`: OK

## Evidencia de conversa real

Transcript completo: `docs/V12_6_CONVERSATION_TRANSCRIPT.md`.

Pontos confirmados:

- consulta de entidade desconhecida nao cai em `unknown`;
- aprendizado novo nao vira `unknown`;
- consulta de entidade conhecida usa World Model/memoria local com `llm_calls=0`;
- capability query local usa `llm_calls=0`;
- unknown recovery nao repete fallback;
- informacao externa atual sem ferramenta nao e inventada.
