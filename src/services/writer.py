"""
Módulo de escritura en ThingSpeak para Stark Reactor IoT Monitor.
Implementa las tareas P3-01, P3-02 y P3-03 (role:write).
"""

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import requests

from src.config import DEFAULT_HTTP_TIMEOUT, ThingSpeakConfig
from src.validation import FIELD_RANGES, ValueErrorKind, parse_measurement

DEFAULT_COOLDOWN_SEC = 15.0


@dataclass(frozen=True)
class ReactorSample:
    """Modelo de datos para los 5 campos del reactor Arc (P3-01)."""
    core_load: float          # field1: Carga del núcleo (%)
    field_stability: float    # field2: Estabilidad del campo (0-100)
    coolant_flow: float       # field3: Flujo de refrigerante (0-100)
    jarvis_latency: float     # field4: Latencia JARVIS (ms)
    repulsor_power: float     # field5: Consumo de repulsores (W)

    def to_thingspeak_payload(self) -> Dict[str, float]:
        return {
            "field1": self.core_load,
            "field2": self.field_stability,
            "field3": self.coolant_flow,
            "field4": self.jarvis_latency,
            "field5": self.repulsor_power,
        }


@dataclass(frozen=True)
class WriteResult:
    """Contrato de respuesta hacia la interfaz de usuario (P3-01, P3-03)."""
    success: bool
    entry_id: Optional[int] = None
    error_message: Optional[str] = None
    cooldown_remaining: float = 0.0
    http_status: Optional[int] = None


def _parse_numeric(value: Any, field_label: str, field_key: str) -> float:
    """Convierte y valida que un valor sea numérico finito."""
    number, error = parse_measurement(value, *FIELD_RANGES.get(field_key, (None, None)))
    if error is ValueErrorKind.REQUIRED:
        if isinstance(value, str):
            raise ValueError(f"El campo '{field_label}' no puede estar vacío.")
        raise ValueError(f"El campo '{field_label}' es obligatorio y debe ser numérico.")
    if error is ValueErrorKind.NOT_NUMERIC:
        raise ValueError(f"El campo '{field_label}' debe ser un número válido.")
    if error is ValueErrorKind.NOT_FINITE:
        raise ValueError(f"El campo '{field_label}' contiene un valor numérico no válido (NaN/Inf).")
    if error is ValueErrorKind.OUT_OF_RANGE:
        low, high = FIELD_RANGES[field_key]
        raise ValueError(f"La variable {field_label.lower()} debe estar entre {low:g} y {high:g}.")
    assert number is not None
    return number


def validate_reactor_sample(
    core_load: Any,
    field_stability: Any,
    coolant_flow: Any,
    jarvis_latency: Any,
    repulsor_power: Any,
) -> Tuple[Optional[ReactorSample], Optional[str]]:
    """
    Valida los 5 campos introducidos manualmente por el usuario (P3-01).
    - Todos los campos deben ser numéricos.
    - Estabilidad (field2) y refrigerante (field3) deben estar entre 0 y 100.
    - No se imponen rangos máximos artificiales al resto de campos.
    """
    try:
        return ReactorSample(
            core_load=_parse_numeric(core_load, "Carga del núcleo (field1)", "field1"),
            field_stability=_parse_numeric(field_stability, "Estabilidad del campo (field2)", "field2"),
            coolant_flow=_parse_numeric(coolant_flow, "Flujo de refrigerante (field3)", "field3"),
            jarvis_latency=_parse_numeric(jarvis_latency, "Latencia JARVIS (field4)", "field4"),
            repulsor_power=_parse_numeric(repulsor_power, "Consumo de repulsores (field5)", "field5"),
        ), None
    except ValueError as err:
        return None, str(err)


class ThingSpeakWriter:
    """Cliente de escritura para ThingSpeak con control de frecuencia (P3-02, P3-03)."""

    def __init__(
        self,
        write_api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cooldown_sec: float = DEFAULT_COOLDOWN_SEC,
        timeout_sec: float = DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        if write_api_key is None or base_url is None:
            config = ThingSpeakConfig.from_env()
            if write_api_key is None:
                write_api_key = config.write_api_key
            if base_url is None:
                base_url = config.base_url
        self.write_api_key = write_api_key
        self.base_url = base_url.rstrip("/")
        self.cooldown_sec = float(cooldown_sec)
        self.timeout_sec = timeout_sec
        self._last_write_timestamp: Optional[float] = None
        self._send_lock = Lock()

    def get_cooldown_remaining(self) -> float:
        """Devuelve los segundos restantes para permitir la siguiente escritura (P3-03)."""
        if self._last_write_timestamp is None:
            return 0.0
        elapsed = time.monotonic() - self._last_write_timestamp
        remaining = self.cooldown_sec - elapsed
        return max(0.0, remaining)

    def send_sample(
        self,
        core_load: Any,
        field_stability: Any,
        coolant_flow: Any,
        jarvis_latency: Any,
        repulsor_power: Any,
    ) -> WriteResult:
        """
        Valida y envía una muestra de 5 campos a ThingSpeak respetando el intervalo de 15 s.
        """
        if not self._send_lock.acquire(blocking=False):
            return WriteResult(
                success=False,
                error_message="Ya hay un envío en curso. Espere a que finalice.",
                cooldown_remaining=self.get_cooldown_remaining(),
            )
        try:
            return self._send_sample(core_load, field_stability, coolant_flow, jarvis_latency, repulsor_power)
        finally:
            self._send_lock.release()

    def _send_sample(
        self,
        core_load: Any,
        field_stability: Any,
        coolant_flow: Any,
        jarvis_latency: Any,
        repulsor_power: Any,
    ) -> WriteResult:
        remaining = self.get_cooldown_remaining()
        if remaining > 0:
            return WriteResult(
                success=False,
                error_message=(
                    f"Debe respetar el intervalo de ThingSpeak. "
                    f"Espere {remaining:.1f} s antes de volver a enviar."
                ),
                cooldown_remaining=remaining,
            )

        sample, validation_error = validate_reactor_sample(
            core_load, field_stability, coolant_flow, jarvis_latency, repulsor_power
        )
        if validation_error or sample is None:
            return WriteResult(success=False, error_message=validation_error)

        if not self.write_api_key or self.write_api_key.upper() == "REEMPLAZAR" or "..." in self.write_api_key:
            return WriteResult(
                success=False,
                error_message=(
                    "THINGSPEAK_WRITE_API_KEY no está configurada o contiene un placeholder. "
                    "Revise su archivo .env local."
                ),
            )

        endpoint = f"{self.base_url}/update"
        params: Dict[str, Any] = {"api_key": self.write_api_key}
        params.update(sample.to_thingspeak_payload())

        try:
            response = requests.get(endpoint, params=params, timeout=self.timeout_sec)
        except requests.Timeout:
            return WriteResult(
                success=False,
                error_message="Tiempo de espera agotado (timeout) al conectar con ThingSpeak.",
            )
        except requests.RequestException:
            return WriteResult(
                success=False,
                error_message="Error de red al conectar con ThingSpeak.",
            )

        if response.status_code != 200:
            return WriteResult(
                success=False,
                error_message=f"ThingSpeak devolvió un error HTTP {response.status_code}.",
                http_status=response.status_code,
            )

        body = response.text.strip()
        try:
            entry_id = int(body)
        except ValueError:
            return WriteResult(
                success=False,
                error_message="Respuesta inesperada de ThingSpeak.",
                http_status=response.status_code,
            )

        if entry_id <= 0:
            return WriteResult(
                success=False,
                error_message=(
                    "ThingSpeak rechazó la escritura (respuesta 0). "
                    "Respete el intervalo mínimo de 15 segundos entre envíos."
                ),
                http_status=response.status_code,
            )

        self._last_write_timestamp = time.monotonic()
        return WriteResult(
            success=True,
            entry_id=entry_id,
            cooldown_remaining=self.cooldown_sec,
            http_status=response.status_code,
        )
