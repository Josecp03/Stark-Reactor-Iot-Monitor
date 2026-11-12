"""Punto de entrada de Stark Reactor IoT Monitor (P4-01).

Uso desde la raíz del proyecto:

    python -m src.main                  # abre la interfaz gráfica
    python -m src.main --check-config   # solo comprueba la configuración
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from src.config import DEFAULT_ENV_PATH, ENV_EXAMPLE_FILENAME, ConfigProblem, ThingSpeakConfig


def describe_config(config: ThingSpeakConfig) -> str:
    """Resume la configuración activa sin mostrar el valor de las claves."""
    env_state = "encontrado" if DEFAULT_ENV_PATH.is_file() else f"no encontrado (copie {ENV_EXAMPLE_FILENAME})"
    write_state = "configurada" if config.write_api_key else "NO configurada"
    read_state = "configurada" if config.read_api_key else "no configurada (canal público)"
    return "\n".join(
        (
            f"Archivo .env:      {env_state}",
            f"Canal ThingSpeak:  {config.channel_id}",
            f"Write API Key:     {write_state}",
            f"Read API Key:      {read_state}",
            f"URL base:          {config.base_url}",
            f"Timeout HTTP:      {config.timeout:g} s",
        )
    )


def report_problems(problems: Sequence[ConfigProblem]) -> None:
    """Escribe los problemas de configuración en la salida de error."""
    for problem in problems:
        print(f"[CONFIGURACIÓN] {problem.message}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Monitor del reactor Arc: envía y consulta mediciones en ThingSpeak.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Comprueba la configuración (.env y variables de entorno) y termina sin abrir la interfaz.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = ThingSpeakConfig.from_env()
    problems = config.problems()

    if args.check_config:
        print(describe_config(config))
        if problems:
            report_problems(problems)
            return 1
        print("Configuración correcta.")
        return 0

    report_problems(problems)

    try:
        from src.ui.app import run_app
    except ModuleNotFoundError as exc:
        print(
            f"[ERROR] Falta el módulo '{exc.name}'. Instale las dependencias con:\n"
            "    pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    return run_app(config, problems)


if __name__ == "__main__":
    raise SystemExit(main())
