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

REM Si .venv pertenece a Linux/WSL, limpiarlo antes de sincronizar en Windows
if exist ".venv\lib64" (
    rmdir ".venv\lib64" >nul 2>nul
    rmdir /s /q ".venv" >nul 2>nul
)

REM Comprobar configuracion
uv run --managed-python python -m src.main --check-config

REM Ejecutar los tests
uv run --managed-python pytest -q

REM Abrir la interfaz grafica
uv run --managed-python python -m src.main
endlocal
