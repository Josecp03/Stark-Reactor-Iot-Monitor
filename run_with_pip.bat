@echo off
setlocal
chcp 65001 >nul 2>nul

REM Ir al directorio raiz del proyecto
cd /d "%~dp0"

REM Si .venv no existe o le falta tkinter/pytest, ejecutar install_with_pip.bat
if not exist ".venv\Scripts\python.exe" (
    call "%~dp0install_with_pip.bat"
    if errorlevel 1 exit /b 1
) else (
    .\.venv\Scripts\python.exe -c "import tkinter, pytest, requests" >nul 2>nul
    if errorlevel 1 (
        call "%~dp0install_with_pip.bat"
        if errorlevel 1 exit /b 1
    )
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
