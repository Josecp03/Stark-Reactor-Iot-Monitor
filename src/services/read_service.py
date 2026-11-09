"""Servicio de lectura de telemetría desde ThingSpeak (Persona 2 — role:read).

Implementa:
- P2-01: Contrato de datos de lectura (`ReactorReading`, `ReadResult`, `FIELD_SPECS`).
- P2-02: Peticiones HTTP GET al endpoint `feeds.json` de ThingSpeak con timeout,
  límite configurable de últimos N registros (`results`) y manejo de errores HTTP/red.
- P2-03: Normalización del JSON de `feeds` en estructuras tipadas y ordenadas,
  convirtiendo cadenas numéricas a `float` y tratando nulos/vacíos de forma segura.
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

from src.config import (
    DEFAULT_BASE_URL,
    DEFAULT_CHANNEL_ID,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_READ_RESULTS,
    ThingSpeakConfig,
)

try:
    import requests  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - fallback a urllib de la librería estándar
    requests = None  # type: ignore[assignment]


@dataclass(frozen=True)
class FieldSpec:
    """Metadatos descriptivos de cada campo del canal ThingSpeak."""

    field_key: str
    semantic_key: str
    label: str
    unit: str


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("field1", "core_load", "Carga de energía del núcleo", "%"),
    FieldSpec("field2", "field_stability", "Estabilidad del campo", "0–100"),
    FieldSpec("field3", "coolant_flow", "Flujo de refrigerante de vibranium", "0–100"),
    FieldSpec("field4", "jarvis_latency", "Latencia del protocolo JARVIS", "ms"),
    FieldSpec("field5", "repulsor_power", "Consumo energético de los repulsores", "W"),
)


@dataclass(frozen=True)
class ReactorReading:
    """Registro individual normalizado de telemetría del reactor Arc (P2-01).

    Contiene `entry_id`, `created_at` y los cinco campos (`field1`..`field5`)
    convertidos a `float` o `None` cuando el dato está ausente o no es numérico.
    Expone además propiedades con nombres semánticos para uso directo en UI y gráficas.
    """

    entry_id: int
    created_at: str
    field1: float | None = None
    field2: float | None = None
    field3: float | None = None
    field4: float | None = None
    field5: float | None = None

    @property
    def core_load(self) -> float | None:
        """Carga de energía del núcleo (%) — `field1`."""
        return self.field1

    @property
    def field_stability(self) -> float | None:
        """Estabilidad del campo (0–100) — `field2`."""
        return self.field2

    @property
    def coolant_flow(self) -> float | None:
        """Flujo de refrigerante de vibranium (0–100) — `field3`."""
        return self.field3

    @property
    def jarvis_latency(self) -> float | None:
        """Latencia del protocolo JARVIS (ms) — `field4`."""
        return self.field4

    @property
    def repulsor_power(self) -> float | None:
        """Consumo energético de los repulsores (W) — `field5`."""
        return self.field5

    @property
    def formatted_timestamp(self) -> str:
        """Marca temporal legible (`YYYY-MM-DD HH:MM:SS UTC`) para la tabla de la UI."""
        return format_timestamp(self.created_at)

    def to_dict(self) -> dict[str, int | float | str | None]:
        """Devuelve una representación en diccionario con claves técnicas y semánticas."""
        return {
            "entry_id": self.entry_id,
            "created_at": self.created_at,
            "formatted_timestamp": self.formatted_timestamp,
            "field1": self.field1,
            "field2": self.field2,
            "field3": self.field3,
            "field4": self.field4,
            "field5": self.field5,
            "core_load": self.field1,
            "field_stability": self.field2,
            "coolant_flow": self.field3,
            "jarvis_latency": self.field4,
            "repulsor_power": self.field5,
        }


@dataclass(frozen=True)
class HttpFetchResult:
    """Resultado de bajo nivel de la petición HTTP GET a ThingSpeak (P2-02)."""

    ok: bool
    status_code: int | None = None
    payload: dict[str, Any] | None = None
    error_message: str | None = None
    url: str = ""


@dataclass(frozen=True)
class ReadResult:
    """Contrato de respuesta del servicio de lectura para la interfaz (P2-01 / P2-03)."""

    ok: bool
    channel_id: str
    records: list[ReactorReading] = field(default_factory=list)
    channel_name: str | None = None
    status_code: int | None = None
    error_message: str | None = None

    @property
    def is_empty(self) -> bool:
        """Indica si la consulta fue correcta pero el canal no tiene registros."""
        return self.ok and len(self.records) == 0


def parse_numeric_field(value: Any) -> float | None:
    """Convierte un valor de campo de ThingSpeak a `float` o `None` (P2-01 / P2-03).

    Reglas:
    - `None`, booleanos o cadenas vacías / espacios -> `None`
    - Cadenas numéricas (`"52.4"`, `" 96.8 "`, `"-10"`) -> `float`
    - Valores `NaN`, `inf` o `-inf` -> `None`
    - Cualquier otro texto o tipo no convertible -> `None`
    """
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"null", "none", "nan", "inf", "-inf", "+inf"}:
            return None
        try:
            numeric = float(cleaned)
        except ValueError:
            return None
        return numeric if math.isfinite(numeric) else None

    return None


def parse_entry_id(value: Any) -> int | None:
    """Convierte `entry_id` a un entero positivo válido, o `None` si no es válido."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            parsed = int(cleaned)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def format_timestamp(raw_timestamp: str | None) -> str:
    """Convierte una cadena ISO-8601 (`2026-11-08T17:20:00Z`) a formato legible."""
    if not raw_timestamp or not isinstance(raw_timestamp, str):
        return ""
    cleaned = raw_timestamp.strip()
    if not cleaned:
        return ""
    try:
        iso_candidate = cleaned.replace("Z", "+00:00") if cleaned.endswith("Z") else cleaned
        dt = datetime.fromisoformat(iso_candidate)
        if cleaned.endswith("Z") or dt.utcoffset() is not None:
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return cleaned


def normalize_feed_entry(raw_entry: Mapping[str, Any]) -> ReactorReading | None:
    """Transforma un objeto `feed` de ThingSpeak en un `ReactorReading` (P2-03).

    Si `raw_entry` no es un mapeo o carece de un `entry_id` válido, devuelve `None`.
    """
    if not isinstance(raw_entry, Mapping):
        return None

    entry_id = parse_entry_id(raw_entry.get("entry_id"))
    if entry_id is None:
        return None

    raw_created_at = raw_entry.get("created_at")
    created_at = raw_created_at.strip() if isinstance(raw_created_at, str) else ""

    return ReactorReading(
        entry_id=entry_id,
        created_at=created_at,
        field1=parse_numeric_field(raw_entry.get("field1")),
        field2=parse_numeric_field(raw_entry.get("field2")),
        field3=parse_numeric_field(raw_entry.get("field3")),
        field4=parse_numeric_field(raw_entry.get("field4")),
        field5=parse_numeric_field(raw_entry.get("field5")),
    )


def normalize_feeds(
    payload_or_feeds: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> list[ReactorReading]:
    """Normaliza la colección `feeds` en una lista ordenada de `ReactorReading` (P2-03).

    Acepta tanto el JSON completo devuelto por ThingSpeak (`{"channel": ..., "feeds": [...]}`)
    como directamente una secuencia de diccionarios `feeds`.
    Los registros se devuelven ordenados ascendentemente por `(entry_id, created_at)`.
    """
    if payload_or_feeds is None:
        return []

    raw_feeds: Any
    if isinstance(payload_or_feeds, Mapping):
        raw_feeds = payload_or_feeds.get("feeds", [])
    elif isinstance(payload_or_feeds, Sequence) and not isinstance(payload_or_feeds, (str, bytes)):
        raw_feeds = payload_or_feeds
    else:
        return []

    if not isinstance(raw_feeds, Sequence) or isinstance(raw_feeds, (str, bytes)):
        return []

    readings: list[ReactorReading] = []
    for item in raw_feeds:
        reading = normalize_feed_entry(item)
        if reading is not None:
            readings.append(reading)

    readings.sort(key=lambda r: (r.entry_id, r.created_at))
    return readings


def build_feeds_url(
    channel_id: str,
    results: int = DEFAULT_READ_RESULTS,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """Construye la URL de consulta `feeds.json` con sus parámetros de query."""
    clean_channel = str(channel_id).strip()
    if not clean_channel:
        raise ValueError("El identificador del canal (channel_id) no puede estar vacío.")
    if not isinstance(results, int) or isinstance(results, bool) or results <= 0:
        raise ValueError("El parámetro 'results' debe ser un entero positivo mayor que cero.")

    clean_base = base_url.strip().rstrip("/") or DEFAULT_BASE_URL
    query_params: dict[str, str] = {"results": str(results)}
    if api_key and api_key.strip():
        query_params["api_key"] = api_key.strip()

    query_string = urllib.parse.urlencode(query_params)
    return f"{clean_base}/channels/{urllib.parse.quote(clean_channel)}/feeds.json?{query_string}"


def _http_get_with_requests(url: str, timeout: float) -> tuple[int, str]:
    """Ejecuta HTTP GET usando la librería `requests`."""
    response = requests.get(
        url,
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    return response.status_code, response.text


def _http_get_with_urllib(url: str, timeout: float) -> tuple[int, str]:
    """Ejecuta HTTP GET usando `urllib.request` de la librería estándar."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = getattr(response, "status", response.getcode())
            body = response.read().decode("utf-8", errors="replace")
            return int(status_code), body
    except urllib.error.HTTPError as exc:
        body = ""
        if exc.fp is not None:
            try:
                body = exc.fp.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
        return int(exc.code), body


def fetch_channel_feeds(
    channel_id: str = DEFAULT_CHANNEL_ID,
    results: int = DEFAULT_READ_RESULTS,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    http_get: Callable[[str, float], tuple[int, str]] | None = None,
) -> HttpFetchResult:
    """Consulta el endpoint `feeds.json` de ThingSpeak mediante HTTP GET (P2-02).

    Gestiona de forma controlada:
    - Argumentos inválidos (`channel_id` vacío, `results <= 0`, `timeout <= 0`).
    - Timeouts (`TimeoutError`, `socket.timeout`, `requests.Timeout`).
    - Errores de red/conexión (`ConnectionError`, `urllib.error.URLError`, `requests.RequestException`).
    - Códigos de estado HTTP distintos de 200 (`400`, `401`, `404`, `500`, etc.).
    - Respuestas con JSON malformado o estructura inesperada.
    """
    try:
        url = build_feeds_url(
            channel_id=channel_id,
            results=results,
            api_key=api_key,
            base_url=base_url,
        )
    except ValueError as exc:
        return HttpFetchResult(
            ok=False,
            status_code=None,
            payload=None,
            error_message=str(exc),
            url="",
        )

    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        return HttpFetchResult(
            ok=False,
            status_code=None,
            payload=None,
            error_message="El parámetro 'timeout' debe ser un número positivo mayor que cero.",
            url=url,
        )

    transport = http_get or (_http_get_with_requests if requests is not None else _http_get_with_urllib)

    try:
        status_code, raw_body = transport(url, float(timeout))
    except Exception as exc:
        if _is_timeout_exception(exc):
            return HttpFetchResult(
                ok=False,
                status_code=None,
                payload=None,
                error_message=(
                    f"Tiempo de espera agotado ({timeout}s) al conectar con ThingSpeak."
                ),
                url=url,
            )
        return HttpFetchResult(
            ok=False,
            status_code=None,
            payload=None,
            error_message=f"Error de conexión al consultar ThingSpeak: {exc}",
            url=url,
        )

    if status_code != 200:
        return HttpFetchResult(
            ok=False,
            status_code=status_code,
            payload=None,
            error_message=_format_http_status_error(status_code, channel_id),
            url=url,
        )

    try:
        parsed_json = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError) as exc:
        return HttpFetchResult(
            ok=False,
            status_code=status_code,
            payload=None,
            error_message=f"La respuesta de ThingSpeak no es un JSON válido: {exc}",
            url=url,
        )

    if not isinstance(parsed_json, dict) or "feeds" not in parsed_json or not isinstance(parsed_json.get("feeds"), list):
        return HttpFetchResult(
            ok=False,
            status_code=status_code,
            payload=None,
            error_message="La respuesta JSON de ThingSpeak no contiene una lista 'feeds' válida.",
            url=url,
        )

    return HttpFetchResult(
        ok=True,
        status_code=status_code,
        payload=parsed_json,
        error_message=None,
        url=url,
    )


def get_latest_readings(
    results: int = DEFAULT_READ_RESULTS,
    channel_id: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
    config: ThingSpeakConfig | None = None,
    http_get: Callable[[str, float], tuple[int, str]] | None = None,
) -> ReadResult:
    """Obtiene y normaliza los últimos `results` registros del canal ThingSpeak (P2-01/02/03).

    Esta es la función principal que debe invocar la interfaz gráfica (Persona 4).
    """
    cfg = config or ThingSpeakConfig.from_env()
    resolved_channel_id = channel_id if channel_id is not None else cfg.channel_id
    resolved_api_key = api_key if api_key is not None else cfg.read_api_key
    resolved_base_url = base_url if base_url is not None else cfg.base_url
    resolved_timeout = timeout if timeout is not None else cfg.timeout

    fetch_result = fetch_channel_feeds(
        channel_id=resolved_channel_id,
        results=results,
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        timeout=resolved_timeout,
        http_get=http_get,
    )

    if not fetch_result.ok or fetch_result.payload is None:
        return ReadResult(
            ok=False,
            channel_id=str(resolved_channel_id).strip(),
            records=[],
            channel_name=None,
            status_code=fetch_result.status_code,
            error_message=fetch_result.error_message,
        )

    channel_info = fetch_result.payload.get("channel")
    channel_name: str | None = None
    if isinstance(channel_info, Mapping):
        raw_name = channel_info.get("name")
        if isinstance(raw_name, str) and raw_name.strip():
            channel_name = raw_name.strip()

    records = normalize_feeds(fetch_result.payload)
    return ReadResult(
        ok=True,
        channel_id=str(resolved_channel_id).strip(),
        records=records,
        channel_name=channel_name,
        status_code=fetch_result.status_code,
        error_message=None,
    )


def _is_timeout_exception(exc: BaseException) -> bool:
    """Detecta si una excepción corresponde a un timeout de red (requests o urllib/socket)."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if requests is not None and isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(exc).lower()


def _format_http_status_error(status_code: int, channel_id: str) -> str:
    """Genera un mensaje de error claro según el código HTTP devuelto por ThingSpeak."""
    if status_code == 400:
        return f"Petición incorrecta a ThingSpeak (HTTP 400) para el canal {channel_id}."
    if status_code in (401, 403):
        return (
            f"Acceso denegado al canal {channel_id} (HTTP {status_code}). "
            "Verifique que el canal sea público o que THINGSPEAK_READ_API_KEY sea válida."
        )
    if status_code == 404:
        return f"No se encontró el canal {channel_id} en ThingSpeak (HTTP 404)."
    if status_code == 429:
        return "Demasiadas peticiones a ThingSpeak (HTTP 429). Espere unos segundos antes de reintentar."
    if status_code >= 500:
        return f"El servidor de ThingSpeak no está disponible temporalmente (HTTP {status_code})."
    return f"Error HTTP {status_code} al consultar el canal {channel_id} en ThingSpeak."


def _main() -> int:
    """Permite probar la lectura del canal desde la línea de comandos (P2-02 / P2-04)."""
    parser = argparse.ArgumentParser(
        description="Consulta registros del canal ThingSpeak del reactor Arc."
    )
    parser.add_argument(
        "--channel-id",
        default=None,
        help=f"ID del canal ThingSpeak (por defecto: {DEFAULT_CHANNEL_ID} o variable THINGSPEAK_CHANNEL_ID).",
    )
    parser.add_argument(
        "--results",
        type=int,
        default=DEFAULT_READ_RESULTS,
        help=f"Número de últimos registros a consultar (por defecto: {DEFAULT_READ_RESULTS}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_HTTP_TIMEOUT,
        help=f"Tiempo máximo de espera en segundos (por defecto: {DEFAULT_HTTP_TIMEOUT}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Imprime el resultado normalizado en formato JSON.",
    )
    args = parser.parse_args()

    result = get_latest_readings(
        results=args.results,
        channel_id=args.channel_id,
        timeout=args.timeout,
    )

    if args.as_json:
        output = {
            "ok": result.ok,
            "channel_id": result.channel_id,
            "channel_name": result.channel_name,
            "status_code": result.status_code,
            "error_message": result.error_message,
            "records": [r.to_dict() for r in result.records],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0 if result.ok else 1

    if not result.ok:
        print(f"[ERROR] No se pudo leer el canal {result.channel_id}: {result.error_message}")
        return 1

    title = f"{result.channel_name} (ID: {result.channel_id})" if result.channel_name else f"Canal {result.channel_id}"
    print(f"=== Lectura correcta de {title} | HTTP {result.status_code} ===")
    if result.is_empty:
        print("El canal no contiene registros actualmente (feeds vacíos).")
        return 0

    print(
        f"{'ID':>4} | {'Fecha (UTC)':<23} | {'field1 (%)':>10} | {'field2':>8} | "
        f"{'field3':>8} | {'field4 (ms)':>11} | {'field5 (W)':>10}"
    )
    print("-" * 92)
    for rec in result.records:
        f1 = f"{rec.field1:.1f}" if rec.field1 is not None else "N/A"
        f2 = f"{rec.field2:.1f}" if rec.field2 is not None else "N/A"
        f3 = f"{rec.field3:.1f}" if rec.field3 is not None else "N/A"
        f4 = f"{rec.field4:.1f}" if rec.field4 is not None else "N/A"
        f5 = f"{rec.field5:.1f}" if rec.field5 is not None else "N/A"
        print(
            f"{rec.entry_id:>4} | {rec.formatted_timestamp:<23} | {f1:>10} | {f2:>8} | "
            f"{f3:>8} | {f4:>11} | {f5:>10}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
