# OpenJarvis

Athena includes a curated runtime subset from
https://github.com/open-jarvis/OpenJarvis, commit
`6e4defd33fb3332eed17be1169c4bb3a6e1a274c`, under Apache License 2.0.
The license is reproduced in `third_party/openjarvis/LICENSE`.

`third_party/openjarvis/UPSTREAM.json` records the SHA-256 of each unchanged
upstream runtime module. The package `__init__.py` files are Athena packaging
shims: they replace upstream eager discovery with explicit imports. The subset
contains the real OrchestratorAgent, ToolExecutor, loop guard, core types/event
bus and selected security helpers. It does not include the full OpenJarvis SDK,
its optional providers, servers, frontend, tools, Rust binary or training suite.

Athena adapters, policy, memory, workspace, procedures, voice and resident code
are maintained separately under `integrations/openjarvis`, `voice`, and `runtime`.
No model weights or training datasets are distributed in the source archive.
