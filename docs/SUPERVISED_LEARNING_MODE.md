# Supervised Learning Mode

O modo supervisionado começa com:

`Athena, aprender.`

Resposta esperada:

`Modo de aprendizado iniciado. Eu não vou guardar tudo. Vou estudar o que acontecer, separar o que parece importante e te mostrar antes de consolidar.`

## O que faz

- observa a conversa atual;
- registra mensagens na sessao ativa;
- separa candidatos;
- classifica tipo e risco;
- sugere destino;
- mostra relatorio;
- aguarda aprovacao humana.

## O que nao faz

- nao salva tudo;
- nao confirma memoria sozinho;
- nao altera codigo;
- nao adiciona fonte externa;
- nao executa acao externa;
- nao deixa a LLMTeacher decidir verdade.

## Fluxo

1. `LearningSessionEngine` abre sessao.
2. `Athena.chat()` registra turnos na sessao.
3. `LearningHarvestWorker` cria candidatos locais.
4. `LearningReportEngine` mostra os candidatos.
5. Rewell aprova, rejeita ou edita.
6. `LearningPromotionEngine` consolida apenas aprovados e apenas em destinos seguros.

## Continuidade

A V13-pre prova que aprendizado aprovado sobrevive a restart.

O aprendizado promovido vai para `long_term_memory` com metadata de origem. Depois de fechar runtime, fechar a instancia, reabrir com o mesmo banco, descartar buffer diario e descartar candidatos locais, Athena ainda consegue responder via `Athena.chat()` usando memoria local, sem LLM.
