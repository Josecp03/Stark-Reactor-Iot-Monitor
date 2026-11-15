#!/usr/bin/env bash
set -euo pipefail

# Ir al directorio raíz del proyecto (compatible con Linux y macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Stark Reactor IoT Monitor - Instalación con pip (Linux / macOS) ==="

# 1. Localizar intérprete de Python 3
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[ERROR] No se encontró Python 3 instalado en el sistema." >&2
    exit 1
fi
echo "[1/3] Usando $($PYTHON_CMD --version)."

# 2. Crear entorno virtual .venv e instalar dependencias con pip
echo "[2/3] Creando entorno virtual '.venv' e instalando requirements.txt..."
"$PYTHON_CMD" -m venv .venv
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
echo "Instalación completada. Comandos disponibles:"
echo "  ./run_with_pip.sh                              # Comprobar, pasar tests y abrir la app"
echo "  ./.venv/bin/python -m src.main                 # Abrir aplicación"
echo "  ./.venv/bin/python -m src.main --check-config  # Comprobar configuración"
echo "  ./.venv/bin/python -m pytest -q                # Ejecutar tests"
