@echo off
setlocal
chcp 65001 >nul 2>nul

REM Ir al directorio raiz del proyecto
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual '.venv'. Ejecuta primero: install_with_pip.bat
    exit /b 1
)

REM Crear .env desde .env.example si aun no existe
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
    )
)

REM Comprobar configuracion
.\.venv\Scripts\python.exe -m src.main --check-config

REM Ejecutar los tests
.\.venv\Scripts\python.exe -m pytest -q

REM Abrir la interfaz grafica
.\.venv\Scripts\python.exe -m src.main
endlocal
