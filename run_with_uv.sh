#!/usr/bin/env bash
set -uo pipefail

# Ir al directorio raíz del proyecto (compatible con Linux y macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Crear .env desde .env.example si aún no existe
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi

# Si .venv pertenece a Windows, limpiarlo antes de sincronizar en Linux/macOS
if [ -d ".venv/Scripts" ]; then
    rm -rf .venv
fi

# Comprobar configuración
uv run --managed-python python -m src.main --check-config

# Ejecutar los tests
uv run --managed-python pytest -q

# Abrir la interfaz gráfica
uv run --managed-python python -m src.main
