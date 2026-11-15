#!/usr/bin/env bash
set -uo pipefail

# Ir al directorio raíz del proyecto (compatible con Linux y macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Si .venv no existe, pertenece a otro SO o su Python no tiene tkinter/pytest, ejecutar install_with_pip.sh
if [ ! -x ".venv/bin/python" ] || ! ./.venv/bin/python -c "import tkinter, pytest, requests" >/dev/null 2>&1; then
    echo "Preparando entorno virtual '.venv' con pip y tkinter..."
    bash "$SCRIPT_DIR/install_with_pip.sh"
fi

# Crear .env desde .env.example si aún no existe
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi

# Comprobar configuración
./.venv/bin/python -m src.main --check-config

# Ejecutar los tests
./.venv/bin/python -m pytest -q

# Abrir la interfaz gráfica
./.venv/bin/python -m src.main
