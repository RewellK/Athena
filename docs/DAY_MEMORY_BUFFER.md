# DayMemoryBuffer

`DayMemoryBuffer` guarda material bruto temporario do dia.

Ele nao e memoria permanente.

Entradas registram:

- origem;
- conteudo;
- tipo de contexto;
- sensibilidade;
- importancia candidata;
- estado runtime associado;
- tags.

Status do buffer:

- `open`
- `studying`
- `reviewed`
- `archived`
- `discarded`

## Politica

Conversas do dia podem ser estudadas, mas nao confirmadas automaticamente.

O bruto deve ter retencao curta e nao deve ser commitado. Apenas candidatos aprovados podem ser promovidos.
