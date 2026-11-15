#!/usr/bin/env bash
set -euo pipefail

# Ir al directorio raíz del proyecto (donde se encuentra este script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Stark Reactor IoT Monitor - Instalación ==="

# 1. Comprobar e instalar uv si no está disponible
if ! command -v uv >/dev/null 2>&1; then
    echo "[1/3] 'uv' no está instalado. Instalando uv..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "[ERROR] Se necesita 'curl' o 'wget' para descargar uv automáticamente." >&2
        exit 1
    fi

    # Añadir las rutas habituales de instalación de uv al PATH de la sesión actual
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if ! command -v uv >/dev/null 2>&1; then
        echo "[ERROR] No se encontró 'uv' en el PATH tras la instalación. Reinicia la terminal." >&2
        exit 1
    fi
else
    echo "[1/3] 'uv' ya está instalado ($(uv --version))."
fi

# 2. Instalar entorno virtual y dependencias (usando Python gestionado por uv con tkinter)
echo "[2/3] Sincronizando entorno virtual y dependencias con uv..."
uv python install 3.12
if [ -f "pyproject.toml" ]; then
    uv sync --managed-python --python 3.12
else
    uv venv --managed-python --python 3.12
    uv pip install -r requirements.txt
fi

# 3. Preparar y configurar el archivo .env local (según README.md)
echo "[3/3] Configurando archivo '.env'..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  -> Creado '.env' a partir de '.env.example'."
    else
        echo "[ERROR] No se encontró '.env.example' para crear '.env'." >&2
        exit 1
    fi
else
    echo "  -> Ya existe '.env'."
fi

# Si THINGSPEAK_WRITE_API_KEY sigue con el placeholder REEMPLAZAR, configurarla
if grep -q "^THINGSPEAK_WRITE_API_KEY=REEMPLAZAR" .env 2>/dev/null; then
    WRITE_KEY="${THINGSPEAK_WRITE_API_KEY:-}"
    if [ -z "$WRITE_KEY" ] && [ -t 0 ]; then
        read -r -p "Introduce THINGSPEAK_WRITE_API_KEY (o pulsa Enter para modo solo lectura): " WRITE_KEY
    fi
    if [ -n "$WRITE_KEY" ]; then
        sed -i.bak "s|^THINGSPEAK_WRITE_API_KEY=.*|THINGSPEAK_WRITE_API_KEY=${WRITE_KEY}|" .env && rm -f .env.bak
        echo "  -> 'THINGSPEAK_WRITE_API_KEY' actualizada en '.env'."
    else
        echo "  -> Aviso: 'THINGSPEAK_WRITE_API_KEY' sigue como REEMPLAZAR (la app abrirá en modo solo lectura)."
    fi
fi

# Comprobar que la configuración es válida antes de ejecutar la aplicación
uv run python -m src.main --check-config || true

echo ""
echo "Instalación completada. Comandos disponibles:"
echo "  ./run_with_uv.sh                           # Comprobar, pasar tests y abrir la app"
echo "  uv run python -m src.main                  # Abrir aplicación"
echo "  uv run python -m src.main --check-config   # Comprobar configuración"
echo "  uv run pytest -q                           # Ejecutar tests"
