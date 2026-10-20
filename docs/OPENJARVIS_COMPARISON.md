# Athena e OpenJarvis após a reconstrução

A Athena anterior acumulava rotas e módulos, mas a existência de um plano ou uma
aprovação não garantia execução real. OpenJarvis oferece um executor de ferramentas
com observações, limites, eventos e proteção contra ciclos.

Agora a Athena **usa esse executor oficial como base**, em uma revisão fixada e
com hashes verificáveis. Não é somente uma inspiração arquitetural. Os adaptadores
mantêm SQLite pessoal, identidade, memória, procedimentos e presença residente.

Não foi incorporado o SDK completo: provedores de nuvem, descoberta de plugins,
telemetria, frontend/servidor e treino do upstream não fazem parte da distribuição.
Isso evita atribuir à Athena funcionalidades que ela ainda não executa neste Mac.
O inventário real pode ser consultado pela ferramenta `self_status`.

A adoção do framework não transforma automaticamente o sistema no JARVIS. Ainda
há qualidade probabilística do modelo, limites de CPU, autorizações de aplicativos,
contas não conectadas e trabalho para generalizar aquisição de habilidades.
[Critérios e limites atuais](REBUILD_ACCEPTANCE.md).

Origem: [OpenJarvis](https://github.com/open-jarvis/OpenJarvis), Apache-2.0.
A revisão e os detalhes de empacotamento estão em `../THIRD_PARTY_NOTICES.md`.
