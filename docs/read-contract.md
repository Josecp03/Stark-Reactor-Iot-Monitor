# Contrato de Datos y Documentación del Módulo de Lectura (`role:read`)

Este documento define el contrato de integración del servicio de lectura ([src/services/read_service.py](file:///Users/luismonzon/Documents/GitHub/Stark-Reactor-Iot-Monitor/src/services/read_service.py)) correspondiente a las tareas **P2-01**, **P2-02**, **P2-03** y **P2-04** para su consumo por:
- **Persona 4 (`role:ui`)**: Vista de consulta e histórico en la interfaz de escritorio.
- **Persona 5 (`role:qa-docs`)**: Matriz de pruebas, validación extremo a extremo y gráficas opcionales.

---

## 1. Contrato de datos (`P2-01`)

### 1.1 Metadatos de campos (`FIELD_SPECS`)
La tupla inmutable `FIELD_SPECS` expone la definición oficial de los cinco campos del canal ThingSpeak `3566091`:

| Clave técnica (`field_key`) | Clave semántica (`semantic_key`) | Etiqueta para UI (`label`) | Unidad / rango (`unit`) |
| :--- | :--- | :--- | :--- |
| `field1` | `core_load` | Carga de energía del núcleo | `%` |
| `field2` | `field_stability` | Estabilidad del campo | `0–100` |
| `field3` | `coolant_flow` | Flujo de refrigerante de vibranium | `0–100` |
| `field4` | `jarvis_latency` | Latencia del protocolo JARVIS | `ms` |
| `field5` | `repulsor_power` | Consumo energético de los repulsores | `W` |

---

### 1.2 Modelo de registro (`ReactorReading`)
Cada entrada de `feeds` devuelta por ThingSpeak se transforma en una instancia inmutable `ReactorReading`:

```python
@dataclass(frozen=True)
class ReactorReading:
    entry_id: int
    created_at: str
    field1: float | None = None  # Alias: .core_load
    field2: float | None = None  # Alias: .field_stability
    field3: float | None = None  # Alias: .coolant_flow
    field4: float | None = None  # Alias: .jarvis_latency
    field5: float | None = None  # Alias: .repulsor_power
```

Propiedades y métodos adicionales para la interfaz:
- `reading.formatted_timestamp -> str`: Devuelve la fecha ISO-8601 formateada como `"YYYY-MM-DD HH:MM:SS UTC"` lista para mostrar en la tabla de la UI.
- `reading.to_dict() -> dict`: Devuelve un diccionario con todas las claves técnicas (`field1`..`field5`), semánticas (`core_load`, etc.), `entry_id`, `created_at` y `formatted_timestamp`.

---

### 1.3 Envoltorio de respuesta (`ReadResult`)
La función principal `get_latest_readings(...)` **nunca propaga excepciones de red ni de parseo** hacia la interfaz gráfica; siempre devuelve un objeto `ReadResult`:

```python
@dataclass(frozen=True)
class ReadResult:
    ok: bool
    channel_id: str
    records: list[ReactorReading]
    channel_name: str | None = None
    status_code: int | None = None
    error_message: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.ok and len(self.records) == 0
```

---

### 1.4 Reglas de negocio para casos especiales

1. **Cadenas numéricas (`"52.4"`, `" 96.8 "`, `"100"`)**:
   - Se convierten automáticamente a `float` (`52.4`, `96.8`, `100.0`).
2. **Valores nulos, vacíos o corruptos (`None`, `""`, `"null"`, `"NaN"`, `"inf"`, texto no numérico)**:
   - Se normalizan a `None` en el campo correspondiente sin descartar el resto del registro ni interrumpir la lectura.
   - La interfaz puede representar `None` como `"N/A"` o `"—"`.
3. **Canales sin registros (`"feeds": []`)**:
   - `result.ok` es `True`, `result.is_empty` es `True`, `result.records` es `[]` y `result.error_message` es `None`.
   - Permite a la UI distinguir entre *"Canal vacío (sin mediciones todavía)"* y *"Error de comunicación con ThingSpeak"*.
4. **Ordenación**:
   - Los registros de `result.records` se entregan siempre ordenados ascendentemente por `(entry_id, created_at)`.

---

## 2. Interfaz pública del módulo (`P2-02` y `P2-03`)

### 2.1 Uso recomendado desde la UI (`Persona 4`)

```python
from src.services.read_service import FIELD_SPECS, get_latest_readings

result = get_latest_readings(results=10)

if not result.ok:
    # Mostrar result.error_message en la barra de estado o diálogo de error
    print(f"Error: {result.error_message}")
elif result.is_empty:
    # Mostrar aviso de canal sin registros
    print("No hay mediciones registradas en el canal.")
else:
    for row in result.records:
        print(
            row.entry_id,
            row.formatted_timestamp,
            row.core_load,        # o row.field1
            row.field_stability,  # o row.field2
            row.coolant_flow,     # o row.field3
            row.jarvis_latency,   # o row.field4
            row.repulsor_power,   # o row.field5
        )
```

### 2.2 Funciones disponibles en `src.services.read_service`

- `get_latest_readings(results=10, channel_id=None, api_key=None, base_url=None, timeout=None) -> ReadResult`:
  Consulta ThingSpeak (usando `.env` o los valores por defecto del canal `3566091`) y devuelve los registros ya normalizados.
- `fetch_channel_feeds(channel_id="3566091", results=10, api_key=None, base_url="https://api.thingspeak.com", timeout=10.0) -> HttpFetchResult`:
  Realiza únicamente la petición HTTP GET y valida el código HTTP y la estructura base del JSON.
- `normalize_feeds(payload_or_feeds) -> list[ReactorReading]`:
  Función pura que transforma el diccionario JSON de ThingSpeak (o una lista `feeds`) en una lista ordenada de `ReactorReading`.
- `normalize_feed_entry(raw_entry) -> ReactorReading | None`:
  Normaliza una única entrada de `feeds`.
- `parse_numeric_field(value) -> float | None`:
  Conversión segura de un valor individual a `float` o `None`.

---

## 3. Verificación por CLI y Pruebas Automatizadas (`P2-04`)

### 3.1 Consultar el canal real `3566091` desde terminal (sin UI)

Tabla formateada en consola:
```bash
python3 -m src.services.read_service --results 10
```

Salida en formato JSON normalizado:
```bash
python3 -m src.services.read_service --results 5 --json
```

Ejemplo de salida en consola:
```text
=== Lectura correcta de Stark Industries - Arc Reactor Monitoring (ID: 3566091) | HTTP 200 ===
  ID | Fecha (UTC)             | field1 (%) |   field2 |   field3 | field4 (ms) | field5 (W)
--------------------------------------------------------------------------------------------
   1 | 2026-11-08 17:01:00 UTC |       52.4 |     96.8 |     35.2 |       118.6 |       42.3
```

### 3.2 Ejecutar la suite de pruebas automatizadas

Con `unittest` (librería estándar, sin dependencias externas):
```bash
python3 -m unittest discover -s tests -v
```

O con `pytest`:
```bash
pytest -v
```

Escenarios cubiertos en [tests/test_read_service.py](file:///Users/luismonzon/Documents/GitHub/Stark-Reactor-Iot-Monitor/tests/test_read_service.py):
1. **Respuesta válida**: normalización completa de las 10 muestras oficiales de [data/reactor_samples.csv](file:///Users/luismonzon/Documents/GitHub/Stark-Reactor-Iot-Monitor/data/reactor_samples.csv).
2. **Canal sin registros**: respuesta con `"feeds": []` verificando `ok=True` e `is_empty=True`.
3. **Campos ausentes y nulos**: `None`, `""`, `"null"`, `"NaN"`, `"inf"` y cadenas no numéricas convertidos a `None` sin pérdida del registro.
4. **Fallos de red y API**: simulación de `Timeout`, `ConnectionError`, códigos HTTP `400`, `401`, `403`, `404`, `429`, `500`, `503` y respuestas con JSON corrupto.
