#!/bin/bash

# Crear .env desde .env.example si aún no existe
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi

# Comprobar configuración
uv run --managed-python python -m src.main --check-config

# Ejecutar los tests
uv run --managed-python pytest -q

# Abrir la interfaz gráfica
uv run --managed-python python -m src.main
