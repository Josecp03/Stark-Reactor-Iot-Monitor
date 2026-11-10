
## 1. Descripción del Módulo
El módulo de escritura (`src/services/writer.py`) se encarga de gestionar de forma segura, robusta y controlada el envío de los cinco parámetros críticos del reactor Arc hacia la plataforma IoT **ThingSpeak**. 

Diseñado bajo un enfoque modular y desacoplado de la interfaz de usuario, este componente garantiza la integridad de los datos mediante validaciones estrictas de rangos y tipos, protege las credenciales de acceso mediante variables de entorno y respeta escrupulosamente los límites de frecuencia (*rate-limit*) impuestos por la plataforma.

---

## 2. Contrato de Datos y Validaciones (`P3-01`)

Para asegurar la correcta comunicación entre la capa de interfaz de usuario (`UI`) y el servicio de red, se han definido dos estructuras de datos principales mediante `dataclasses`:

* **`ReactorSample`**: Modelo inmutable que agrupa las cinco métricas del sistema:
  * `core_load` (Carga del núcleo, `field1`): Valor numérico real (sin topes máximos artificiales).
  * `field_stability` (Estabilidad del campo, `field2`): Valor numérico con rango estricto **$[0, 100]$**.
  * `coolant_flow` (Flujo de refrigerante, `field3`): Valor numérico con rango estricto **$[0, 100]$**.
  * `jarvis_latency` (Latencia JARVIS, `field4`): Valor numérico en milisegundos.
  * `repulsor_power` (Consumo de repulsores, `field5`): Valor numérico en vatios.
* **`WriteResult`**: Objeto de respuesta normalizado hacia la UI que encapsula el estado de la operación (`success`), el identificador único devuelto por ThingSpeak (`entry_id`), mensajes descriptivos de error (`error_message`), el código de estado HTTP y el tiempo de espera restante (*cooldown*).

### Reglas de Validación Implementadas
Antes de construir la petición HTTP, la función `validate_reactor_sample(...)` comprueba:
1. Que ningún campo sea nulo, booleano, cadena vacía o contenga valores no numéricos (`NaN` o `Inf`).
2. Que las comas decimales (formato local) se normalicen automáticamente a puntos.
3. Que la estabilidad del campo y el flujo de refrigerante se encuentren estrictamente comprendidos entre 0 y 100, rechazando cualquier valor fuera de rango con un mensaje descriptivo para el usuario.

---

## 3. Comunicación HTTP y Endpoint de ThingSpeak (`P3-02`)

El envío de los datos se realiza empleando el método HTTP `GET` contra la API oficial de ThingSpeak, tal como se especifica en la pestaña *API Requests* de la plataforma y en los anexos del enunciado:

* **Endpoint base:** `https://api.thingspeak.com/update`
* **Parámetros enviados en la query string:**
  * `api_key`: Clave secreta de escritura (`THINGSPEAK_WRITE_API_KEY`), cargada de forma segura desde el entorno local (`.env`) mediante `python-dotenv`.
  * `field1` a `field5`: Valores numéricos validados de la muestra del reactor.

### Manejo de Respuestas y Errores
* **Código HTTP 200 OK:** Se lee el cuerpo de la respuesta (`response.text.strip()`). 
  * Si ThingSpeak devuelve un número entero positivo mayor que `0` (ej. `1`, `42`), se interpreta como el `entry_id` de la inserción exitosa.
  * Si ThingSpeak devuelve `0`, indica que la plataforma ha rechazado la escritura debido a una violación del intervalo de frecuencia o error de validación en servidor.
* **Excepciones de red:** Se capturan de forma controlada timeouts (`requests.Timeout`) y fallos generales de conectividad (`requests.RequestException`), devolviendo un objeto `WriteResult` con `success=False` sin interrumpir la ejecución de la aplicación.

---

## 4. Control de Frecuencia (*Rate Limiting*) y Anti-Doble Clic (`P3-03`)

ThingSpeak establece por defecto una restricción temporal entre escrituras consecutivas (fijada en **15 segundos** en la capa gratuita). Para evitar bloqueos por parte de la plataforma y mejorar la experiencia de usuario:

1. **Protección Anti-Doble Clic (`_in_flight`):** Se bloquean peticiones concurrentes si ya hay un envío en curso.
2. **Temporizador de Cooldown (`time.monotonic()`):** 
   Tras cada envío exitoso, el servicio registra la marca temporal exacta.
   Si el usuario intenta enviar otra muestra antes de que transcurran 15 segundos, el método `send_sample` frena la ejecución localmente sin realizar peticiones de red, informando mediante `cooldown_remaining` del tiempo exacto que falta para permitir el siguiente envío.

---

## 5. Pruebas Automatizadas y Validación (`P3-04`)

El módulo cuenta con una completa batería de pruebas unitarias implementada con **`pytest`** y **`unittest.mock`** (`tests/test_writer.py`), la cual verifica de forma aislada:
* La correcta validación de entradas válidas y casos límite (números negativos, cadenas vacías, valores fuera de rango en `field2` y `field3`).
* El comportamiento ante la ausencia de la clave de escritura en el entorno.
* El éxito en la comunicación simulada con ThingSpeak y la activación automática del contador de *cooldown*.
* El bloqueo preventivo ante intentos de escritura prematuros (antes de los 15 s).
* El manejo robusto de respuestas `0` de ThingSpeak, errores HTTP (ej. código `500`) y excepciones por `Timeout`.

Para ejecutar la batería de tests de escritura desde la raíz del proyecto con el entorno virtual activo:
```powershell
python -m pytest tests/test_writer.py -v
```

---


```
