# Servicio de Escritura (`src/services/writer.py`)

## 1. Descripción
El módulo `src/services/writer.py` envía las mediciones del reactor Arc al canal de ThingSpeak. Valida los tipos y rangos de entrada antes de construir la petición, lee la clave de escritura desde el entorno (`.env`) y aplica el intervalo mínimo de 15 segundos entre envíos consecutivos.

## 2. Estructuras de datos y validaciones

Se definen dos `dataclasses`:

- `ReactorSample`: agrupa las cinco variables del canal:
  - `core_load` (`field1`): carga del núcleo (%).
  - `field_stability` (`field2`): estabilidad del campo, en el rango `[0, 100]`.
  - `coolant_flow` (`field3`): flujo de refrigerante, en el rango `[0, 100]`.
  - `jarvis_latency` (`field4`): latencia del protocolo JARVIS (ms).
  - `repulsor_power` (`field5`): consumo de repulsores (W).
- `WriteResult`: resultado devuelto a la interfaz con `success`, `entry_id`, `error_message`, `http_status` y `cooldown_remaining`.

La función `validate_reactor_sample(...)` comprueba que todos los campos sean números finitos (aceptando punto o coma decimal) y que `field2` y `field3` estén entre 0 y 100.

## 3. Petición HTTP a ThingSpeak

- **Método y endpoint:** `GET https://api.thingspeak.com/update`
- **Parámetros query:** `api_key` (`THINGSPEAK_WRITE_API_KEY`) y `field1`..`field5`.
- **Respuestas:**
  - HTTP `200` con un entero mayor que `0`: inserción correcta (el número devuelto es el `entry_id`).
  - HTTP `200` con cuerpo `0`: escritura rechazada por ThingSpeak.
  - Errores HTTP o de red (`requests.Timeout`, `requests.RequestException`): se capturan y devuelven en `WriteResult(success=False, ...)`.

## 4. Control de frecuencia (15 s)

ThingSpeak limita las escrituras en su plan gratuito a una cada 15 segundos:
1. Un `Lock` impide lanzar dos envíos simultáneos desde distintos hilos.
2. Tras cada envío confirmado se guarda `time.monotonic()`. Si se intenta enviar antes de cumplir los 15 segundos, `send_sample` devuelve directamente el tiempo restante en `cooldown_remaining` sin hacer otra petición HTTP.

## 5. Pruebas

Para ejecutar las pruebas del módulo (`tests/test_writer.py`):
```powershell
uv run pytest tests/test_writer.py -v
```
