# Memory Governance

`MemoryGovernanceEngine` cria uma visão administrativa das camadas de memória sem apagar nada automaticamente.

Camadas reconhecidas:

- conversa bruta;
- memória de trabalho;
- candidato de curto prazo;
- memória semântica;
- fatos do World Model;
- memória relacional;
- memória episódica;
- memória consolidada;
- memória de evidência;
- memória procedural/pesquisa;
- memória de melhoria.

Estados usados:

- `raw`;
- `candidate`;
- `pending_confirmation`;
- `confirmed`;
- `consolidated`;
- `stale`;
- `archived`;
- `rejected`.

Política de limpeza:

Athena pode sugerir revisão, arquivamento ou consolidação. Ela não deleta memória automaticamente sem política e revisão humana.
