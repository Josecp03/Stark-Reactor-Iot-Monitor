@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>nul

REM Ir al directorio raiz del proyecto
cd /d "%~dp0"

echo === Stark Reactor IoT Monitor - Instalacion con pip (Windows) ===

REM 1. Localizar interprete de Python
set "PYTHON_CMD="
python --version >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
) else (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    )
)

if "!PYTHON_CMD!"=="" (
    echo [ERROR] No se encontro Python 3 instalado. Instala Python 3.11+ o usa install_with_uv.bat.
    exit /b 1
)

for /f "delims=" %%v in ('!PYTHON_CMD! --version') do set "PY_VER=%%v"
echo [1/3] Usando !PY_VER!.

REM 2. Crear entorno virtual .venv e instalar requirements.txt con pip
echo [2/3] Creando entorno virtual '.venv' e instalando requirements.txt...
!PYTHON_CMD! -m venv .venv
if errorlevel 1 exit /b 1

.\.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

REM 3. Preparar y configurar el archivo .env local (segun README.md)
echo [3/3] Configurando archivo '.env'...
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo   -^> Creado '.env' a partir de '.env.example'.
    ) else (
        echo [ERROR] No se encontro '.env.example' para crear '.env'.
        exit /b 1
    )
) else (
    echo   -^> Ya existe '.env'.
)

REM Si THINGSPEAK_WRITE_API_KEY sigue con el placeholder REEMPLAZAR, configurarla
findstr /b /c:"THINGSPEAK_WRITE_API_KEY=REEMPLAZAR" ".env" >nul 2>nul
if not errorlevel 1 (
    set "WRITE_KEY=%THINGSPEAK_WRITE_API_KEY%"
    if "!WRITE_KEY!"=="" (
        set /p "WRITE_KEY=Introduce THINGSPEAK_WRITE_API_KEY (o pulsa Enter para modo solo lectura): "
    )
    if not "!WRITE_KEY!"=="" (
        powershell -NoProfile -Command "(Get-Content '.env') -replace '^THINGSPEAK_WRITE_API_KEY=.*', ('THINGSPEAK_WRITE_API_KEY=' + $env:WRITE_KEY) | Set-Content '.env' -Encoding UTF8"
        echo   -^> 'THINGSPEAK_WRITE_API_KEY' actualizada en '.env'.
    ) else (
        echo   -^> Aviso: 'THINGSPEAK_WRITE_API_KEY' sigue como REEMPLAZAR (la app abrira en modo solo lectura).
    )
)

REM Comprobar que la configuracion es valida antes de ejecutar la aplicacion
.\.venv\Scripts\python.exe -m src.main --check-config

echo.
echo Instalacion completada. Comandos disponibles:
echo   run_with_pip.bat                                   # Comprobar, pasar tests y abrir la app
echo   .\.venv\Scripts\python.exe -m src.main             # Abrir aplicacion
echo   .\.venv\Scripts\python.exe -m src.main --check-config  # Comprobar configuracion
echo   .\.venv\Scripts\python.exe -m pytest -q            # Ejecutar tests
endlocal
