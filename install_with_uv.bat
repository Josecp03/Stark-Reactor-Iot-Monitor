@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>nul

REM Ir al directorio raiz del proyecto (donde se encuentra este script)
cd /d "%~dp0"

echo === Stark Reactor IoT Monitor - Instalacion (Windows) ===

REM 1. Comprobar e instalar uv si no esta disponible
where uv >nul 2>nul
if errorlevel 1 (
    echo [1/3] 'uv' no esta instalado. Instalando uv...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
    where uv >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] No se encontro 'uv' en el PATH tras la instalacion. Reinicia la terminal.
        exit /b 1
    )
) else (
    for /f "delims=" %%v in ('uv --version') do set "UV_VER=%%v"
    echo [1/3] 'uv' ya esta instalado (!UV_VER!).
)

REM 2. Instalar entorno virtual y dependencias (usando Python 3.12 gestionado por uv con tkinter)
echo [2/3] Sincronizando entorno virtual y dependencias con uv...
uv python install 3.12
if errorlevel 1 exit /b 1

if exist "pyproject.toml" (
    uv sync --managed-python --python 3.12
    if errorlevel 1 exit /b 1
) else (
    uv venv --managed-python --python 3.12
    if errorlevel 1 exit /b 1
    uv pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

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
uv run --managed-python python -m src.main --check-config

echo.
echo Instalacion completada. Comandos disponibles:
echo   run_with_uv.bat                            # Comprobar, pasar tests y abrir la app
echo   uv run python -m src.main                  # Abrir aplicacion
echo   uv run python -m src.main --check-config   # Comprobar configuracion
echo   uv run pytest -q                           # Ejecutar tests
endlocal
