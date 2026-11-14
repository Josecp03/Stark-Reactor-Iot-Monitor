"""
Módulo de escritura en ThingSpeak para Stark Reactor IoT Monitor.
Implementa las tareas P3-01, P3-02 y P3-03 (role:write).
"""

import math
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://api.thingspeak.com"
DEFAULT_TIMEOUT_SEC = 10
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


def _parse_numeric(value: Any, field_label: str) -> float:
    """Convierte y valida que un valor sea numérico finito."""
    if value is None or isinstance(value, bool):
        raise ValueError(f"El campo '{field_label}' es obligatorio y debe ser numérico.")
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value:
            raise ValueError(f"El campo '{field_label}' no puede estar vacío.")
    try:
        num = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"El campo '{field_label}' debe ser un número válido.") from exc

    if math.isnan(num) or math.isinf(num):
        raise ValueError(f"El campo '{field_label}' contiene un valor numérico no válido (NaN/Inf).")
    return num


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
        f1 = _parse_numeric(core_load, "Carga del núcleo (field1)")
        f2 = _parse_numeric(field_stability, "Estabilidad del campo (field2)")
        f3 = _parse_numeric(coolant_flow, "Flujo de refrigerante (field3)")
        f4 = _parse_numeric(jarvis_latency, "Latencia JARVIS (field4)")
        f5 = _parse_numeric(repulsor_power, "Consumo de repulsores (field5)")

        if not (0.0 <= f2 <= 100.0):
            return None, "La estabilidad del campo (field2) debe estar entre 0 y 100."

        if not (0.0 <= f3 <= 100.0):
            return None, "El flujo de refrigerante (field3) debe estar entre 0 y 100."

        return ReactorSample(
            core_load=f1,
            field_stability=f2,
            coolant_flow=f3,
            jarvis_latency=f4,
            repulsor_power=f5,
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
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self.write_api_key = (
            write_api_key
            if write_api_key is not None
            else os.getenv("THINGSPEAK_WRITE_API_KEY", "").strip()
        )
        raw_url = (
            base_url
            if base_url is not None
            else os.getenv("THINGSPEAK_BASE_URL", DEFAULT_BASE_URL).strip()
        )
        self.base_url = raw_url.rstrip("/")
        self.cooldown_sec = float(cooldown_sec)
        self.timeout_sec = int(timeout_sec)
        self._last_write_timestamp: Optional[float] = None
        self._in_flight: bool = False

    def get_cooldown_remaining(self) -> float:
        """Devuelve los segundos restantes para permitir la siguiente escritura (P3-03)."""
        if self._last_write_timestamp is None:
            return 0.0
        elapsed = time.monotonic() - self._last_write_timestamp
        remaining = self.cooldown_sec - elapsed
        return max(0.0, round(remaining, 1))

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
        # 1. Evitar envíos simultáneos por doble clic (P3-03)
        if self._in_flight:
            return WriteResult(
                success=False,
                error_message="Ya hay un envío en curso. Espere a que finalice.",
                cooldown_remaining=self.get_cooldown_remaining(),
            )

        # 2. Comprobar intervalo mínimo entre escrituras antes de tocar la red (P3-03)
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

        # 3. Validar los 5 valores de entrada (P3-01)
        sample, validation_error = validate_reactor_sample(
            core_load, field_stability, coolant_flow, jarvis_latency, repulsor_power
        )
        if validation_error or sample is None:
            return WriteResult(success=False, error_message=validation_error)

        # 4. Comprobar que la clave de escritura está configurada (P3-02)
        if not self.write_api_key or "..." in self.write_api_key:
            return WriteResult(
                success=False,
                error_message=(
                    "THINGSPEAK_WRITE_API_KEY no está configurada o contiene un placeholder. "
                    "Revise su archivo .env local."
                ),
            )

        # 5. Enviar petición a ThingSpeak (P3-02)
        endpoint = f"{self.base_url}/update"
        params: Dict[str, Any] = {"api_key": self.write_api_key}
        params.update(sample.to_thingspeak_payload())

        self._in_flight = True
        try:
            response = requests.get(endpoint, params=params, timeout=self.timeout_sec)
        except requests.Timeout:
            return WriteResult(
                success=False,
                error_message="Tiempo de espera agotado (timeout) al conectar con ThingSpeak.",
            )
        except requests.RequestException as exc:
            return WriteResult(
                success=False,
                error_message=f"Error de red al conectar con ThingSpeak: {exc}",
            )
        finally:
            self._in_flight = False

        # 6. Verificar código HTTP (P3-02)
        if response.status_code != 200:
            return WriteResult(
                success=False,
                error_message=f"ThingSpeak devolvió un error HTTP {response.status_code}.",
                http_status=response.status_code,
            )

        # 7. Verificar cuerpo de respuesta (0 = rechazado / límite de frecuencia) (P3-02, P3-03)
        body = response.text.strip()
        try:
            entry_id = int(body)
        except ValueError:
            return WriteResult(
                success=False,
                error_message=f"Respuesta inesperada de ThingSpeak: '{body}'.",
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

        # 8. Éxito confirmado: activar cooldown de 15 s (P3-03)
        self._last_write_timestamp = time.monotonic()
        return WriteResult(
            success=True,
            entry_id=entry_id,
            cooldown_remaining=self.cooldown_sec,
            http_status=response.status_code,
        )