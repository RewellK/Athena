# ModuleProposalEngine

`ModuleProposalEngine` cria propostas técnicas de módulos a partir de lacunas de capacidade.

Uma `ModuleProposal` contém:

- `title`;
- `domain`;
- `reason`;
- `required_sources`;
- `required_inputs`;
- `risks`;
- `suggested_tests`;
- `documentation_needed`;
- `acceptance_criteria`;
- `evidence_required`;
- `human_approval_required`;
- `status`.

Status possíveis:

- `proposed`;
- `pending_human_review`;
- `approved`;
- `rejected`;
- `implemented`;
- `deprecated`.

Importante: proposta não é implementação automática. A Athena registra, lista, aprova ou rejeita a proposta, mas não altera código nem instala dependências sozinha.
