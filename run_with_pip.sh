#!/usr/bin/env bash
set -uo pipefail

# Ir al directorio raíz del proyecto (compatible con Linux y macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x ".venv/bin/python" ]; then
    echo "[ERROR] No se encontró el entorno virtual '.venv'. Ejecuta primero: bash install_with_pip.sh" >&2
    exit 1
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
