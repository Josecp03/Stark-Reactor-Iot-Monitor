@echo off
setlocal
chcp 65001 >nul 2>nul

REM Ir al directorio raiz del proyecto
cd /d "%~dp0"

REM Crear .env desde .env.example si aun no existe
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
    )
)

REM Comprobar configuracion
uv run --managed-python python -m src.main --check-config

REM Ejecutar los tests
uv run --managed-python pytest -q

REM Abrir la interfaz grafica
uv run --managed-python python -m src.main
endlocal
