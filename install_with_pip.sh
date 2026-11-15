#!/usr/bin/env bash
set -euo pipefail

# Ir al directorio raíz del proyecto (compatible con Linux y macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Stark Reactor IoT Monitor - Instalación con pip (Linux / macOS) ==="

# Función auxiliar: comprueba si un ejecutable de Python >= 3.11 tiene tkinter y venv
has_tkinter_and_venv() {
    "$1" -c "import sys, tkinter, venv; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1
}

# 1. Localizar un intérprete de Python 3.11+ que incluya tkinter y venv
PYTHON_CMD=""
for candidate in python3.12 python3.13 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && has_tkinter_and_venv "$candidate"; then
        PYTHON_CMD="$(command -v "$candidate")"
        break
    fi
done

# Si el Python del sistema no tiene tkinter (p. ej. Ubuntu/WSL), buscar o descargar Python 3.12 con tkinter
if [ -z "$PYTHON_CMD" ]; then
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if command -v uv >/dev/null 2>&1; then
        echo "[1/3] El Python del sistema no incluye 'tkinter'. Obteniendo Python 3.12 completo..."
        uv python install 3.12 >/dev/null
        PYTHON_CMD="$(uv python find --managed-python 3.12)"
    elif command -v apt-get >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1; then
        echo "[1/3] Instalando 'python3-tk' y 'python3-venv' con apt..."
        sudo apt-get update && sudo apt-get install -y python3-tk python3-venv python3-pip
        PYTHON_CMD="$(command -v python3)"
    else
        echo "[ERROR] No se encontró un Python 3.11+ con 'tkinter' instalado." >&2
        exit 1
    fi
fi

echo "[1/3] Usando $($PYTHON_CMD --version) ($PYTHON_CMD)."

# 2. Recrear entorno virtual .venv limpio con pip e instalar requirements.txt
echo "[2/3] Creando entorno virtual '.venv' con pip e instalando requirements.txt..."
rm -rf .venv
"$PYTHON_CMD" -m venv .venv
./.venv/bin/python -m ensurepip --upgrade >/dev/null 2>&1 || true
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

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
./.venv/bin/python -m src.main --check-config || true

echo ""
echo "Instalación con pip completada. Comandos disponibles:"
echo "  ./run_with_pip.sh                              # Comprobar, pasar tests y abrir la app"
echo "  ./.venv/bin/python -m src.main                 # Abrir aplicación"
echo "  ./.venv/bin/python -m src.main --check-config  # Comprobar configuración"
echo "  ./.venv/bin/python -m pytest -q                # Ejecutar tests"
