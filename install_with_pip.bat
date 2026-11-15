@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>nul

REM Ir al directorio raiz del proyecto
cd /d "%~dp0"

echo === Stark Reactor IoT Monitor - Instalacion con pip (Windows) ===

REM 1. Localizar un interprete de Python 3.12+ (o 3.11+) real que incluya tkinter y venv
set "PYTHON_CMD="
if exist "%APPDATA%\uv\python\cpython-3.12-windows-x86_64-none\python.exe" (
    set "PYTHON_CMD=%APPDATA%\uv\python\cpython-3.12-windows-x86_64-none\python.exe"
)

if "!PYTHON_CMD!"=="" (
    py -3.12 -c "import sys, tkinter, venv" >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%p in ('py -3.12 -c "import sys; print(sys.executable)"') do set "PYTHON_CMD=%%p"
    )
)

if "!PYTHON_CMD!"=="" (
    where uv >nul 2>nul
    if not errorlevel 1 (
        echo [1/3] Obteniendo Python 3.12 con tkinter...
        uv python install 3.12 >nul 2>nul
        for /f "delims=" %%p in ('uv python find --managed-python 3.12 2^>nul') do set "PYTHON_CMD=%%p"
    )
)

if "!PYTHON_CMD!"=="" (
    python -c "import sys, tkinter, venv; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%p in ('python -c "import sys; print(sys.executable)"') do set "PYTHON_CMD=%%p"
    )
)

if "!PYTHON_CMD!"=="" (
    py -3 -c "import sys, tkinter, venv; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%p in ('py -3 -c "import sys; print(sys.executable)"') do set "PYTHON_CMD=%%p"
    )
)

if "!PYTHON_CMD!"=="" (
    echo [ERROR] No se encontro Python 3.11+ con tkinter instalado.
    exit /b 1
)

for /f "delims=" %%v in ('"!PYTHON_CMD!" --version') do set "PY_VER=%%v"
echo [1/3] Usando !PY_VER! (!PYTHON_CMD!).

REM 2. Recrear entorno virtual .venv limpio con pip e instalar requirements.txt
echo [2/3] Creando entorno virtual '.venv' con pip e instalando requirements.txt...
if exist ".venv\lib64" rmdir ".venv\lib64" >nul 2>nul
if exist ".venv" rmdir /s /q ".venv" >nul 2>nul

"!PYTHON_CMD!" -m venv .venv
if errorlevel 1 exit /b 1

.\.venv\Scripts\python.exe -m ensurepip --upgrade >nul 2>nul
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
        powershell -NoProfile -Command "$c = Get-Content '.env'; $c -replace '^THINGSPEAK_WRITE_API_KEY=.*', ('THINGSPEAK_WRITE_API_KEY=' + $env:WRITE_KEY) | Set-Content '.env' -Encoding UTF8"
        echo   -^> 'THINGSPEAK_WRITE_API_KEY' actualizada en '.env'.
    ) else (
        echo   -^> Aviso: 'THINGSPEAK_WRITE_API_KEY' sigue como REEMPLAZAR - modo solo lectura.
    )
)

REM Comprobar que la configuracion es valida antes de ejecutar la aplicacion
.\.venv\Scripts\python.exe -m src.main --check-config

echo.
echo Instalacion con pip completada. Comandos disponibles:
echo   run_with_pip.bat                                       # Comprobar, pasar tests y abrir la app
echo   .\.venv\Scripts\python.exe -m src.main                 # Abrir aplicacion
echo   .\.venv\Scripts\python.exe -m src.main --check-config  # Comprobar configuracion
echo   .\.venv\Scripts\python.exe -m pytest -q                # Ejecutar tests
endlocal
