"""Configuración centralizada de Stark Reactor IoT Monitor.

Carga las variables de configuración desde un archivo `.env` (si existe) y
desde las variables de entorno del sistema, proporcionando valores por defecto
seguros para el canal público de ThingSpeak (3566091).
"""

from __future__ import annotations

import os
from math import isfinite
from dataclasses import dataclass
from pathlib import Path

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"

# Valores por defecto del proyecto (canal público del equipo)
DEFAULT_CHANNEL_ID = "3566091"
DEFAULT_BASE_URL = "https://api.thingspeak.com"
DEFAULT_HTTP_TIMEOUT = 10.0
DEFAULT_READ_RESULTS = 10


def load_dotenv_file(env_path: Path | str | None = None) -> None:
    """Carga variables de un archivo `.env` sin sobrescribir el entorno actual.

    Utiliza `python-dotenv` si está instalado; en caso contrario, emplea un
    lector ligero compatible con el formato `CLAVE=VALOR` estándar.
    """
    path = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH
    if not path.is_file():
        return

    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]

        load_dotenv(dotenv_path=path, override=False)
        return
    except ImportError:
        pass

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


ENV_EXAMPLE_FILENAME = ".env.example"

# Variables obligatorias para que la aplicación pueda leer y escribir en el canal
REQUIRED_ENV_VARS: tuple[str, ...] = ("THINGSPEAK_CHANNEL_ID", "THINGSPEAK_WRITE_API_KEY")


@dataclass(frozen=True)
class ConfigProblem:
    """Problema de configuración que se muestra al usuario sin revelar secretos."""

    variable: str
    message: str
    blocks_write: bool = False
    blocks_read: bool = False


@dataclass(frozen=True)
class ThingSpeakConfig:
    """Parámetros de conexión con ThingSpeak."""

    channel_id: str = DEFAULT_CHANNEL_ID
    read_api_key: str | None = None
    write_api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_HTTP_TIMEOUT

    def problems(self) -> list[ConfigProblem]:
        """Comprueba las variables obligatorias y devuelve los problemas encontrados.

        Los mensajes nunca incluyen el valor de las claves.
        """
        found: list[ConfigProblem] = []

        if not self.channel_id.isdigit():
            found.append(
                ConfigProblem(
                    variable="THINGSPEAK_CHANNEL_ID",
                    message=(
                        "THINGSPEAK_CHANNEL_ID debe ser el identificador numérico del canal "
                        f"(por ejemplo {DEFAULT_CHANNEL_ID}). Revise el archivo .env."
                    ),
                    blocks_write=True,
                    blocks_read=True,
                )
            )

        if self.write_api_key is None:
            found.append(
                ConfigProblem(
                    variable="THINGSPEAK_WRITE_API_KEY",
                    message=(
                        "Falta THINGSPEAK_WRITE_API_KEY: no se podrán enviar muestras. "
                        f"Copie {ENV_EXAMPLE_FILENAME} a .env y escriba la Write API Key "
                        "de la pestaña 'API Keys' del canal."
                    ),
                    blocks_write=True,
                )
            )

        return found

    @property
    def can_write(self) -> bool:
        """Indica si la configuración permite enviar muestras al canal."""
        return not any(p.blocks_write for p in self.problems())

    @property
    def can_read(self) -> bool:
        """Indica si la configuración permite consultar el canal."""
        return not any(p.blocks_read for p in self.problems())

    @classmethod
    def from_env(cls, env_path: Path | str | None = None) -> ThingSpeakConfig:
        """Construye la configuración leyendo variables de entorno y `.env`."""
        load_dotenv_file(env_path)

        channel_id = os.getenv("THINGSPEAK_CHANNEL_ID", DEFAULT_CHANNEL_ID).strip() or DEFAULT_CHANNEL_ID
        raw_read_key = os.getenv("THINGSPEAK_READ_API_KEY", "").strip()
        raw_write_key = os.getenv("THINGSPEAK_WRITE_API_KEY", "").strip()
        base_url = os.getenv("THINGSPEAK_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL

        # Ignorar placeholders de ejemplo como "REEMPLAZAR" o "...""
        read_api_key = (
            None
            if not raw_read_key or raw_read_key.upper() == "REEMPLAZAR" or raw_read_key.endswith("...")
            else raw_read_key
        )
        write_api_key = (
            None
            if not raw_write_key or raw_write_key.upper() == "REEMPLAZAR" or raw_write_key.endswith("...")
            else raw_write_key
        )

        raw_timeout = os.getenv("THINGSPEAK_HTTP_TIMEOUT", str(DEFAULT_HTTP_TIMEOUT)).strip()
        try:
            timeout = float(raw_timeout)
            if not isfinite(timeout) or timeout <= 0:
                timeout = DEFAULT_HTTP_TIMEOUT
        except ValueError:
            timeout = DEFAULT_HTTP_TIMEOUT

        return cls(
            channel_id=channel_id,
            read_api_key=read_api_key,
            write_api_key=write_api_key,
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )
