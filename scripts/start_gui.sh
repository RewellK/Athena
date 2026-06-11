#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
else
    echo "Athena: ambiente virtual 'venv' não encontrado em $PROJECT_ROOT."
    echo "Vou tentar usar o Python disponível no sistema."
fi

PYTHON_BIN="${PYTHON:-python3}"

"$PYTHON_BIN" - <<'PY'
try:
    import customtkinter  # noqa: F401
except Exception as error:
    raise SystemExit(
        "Athena: dependência da GUI ausente: customtkinter.\n"
        "Instale as dependências no venv do projeto e tente novamente.\n"
        f"Detalhe: {error}"
    )
PY

exec "$PYTHON_BIN" app.py
