# Integración con ThingSpeak

## 1. Configuración del canal

La plataforma ThingSpeak se utiliza para almacenar y consultar las mediciones del reactor Arc de Stark Industries.

- **Nombre:** Stark Industries - Arc Reactor Monitoring
- **Channel ID:** `3566091`
- **Author:** `mwa0000042894849`
- **Acceso:** público
- **URL:** https://thingspeak.mathworks.com/channels/3566091

## 2. Campos configurados

| Campo | Variable | Unidad |
|---|---|---|
| field1 | Core Energy Load | % |
| field2 | Field Stability | 0–100 |
| field3 | Vibranium Coolant Flow | 0–100 |
| field4 | JARVIS Protocol Latency | ms |
| field5 | Repulsor Power Consumption | W |

## 3. Lectura mediante API REST

**Método:** GET

**Endpoint:**

`https://api.thingspeak.com/channels/3566091/feeds.json?results=10`

Este endpoint permite consultar los últimos diez registros almacenados en el canal público.

La respuesta contiene información del canal y una colección `feeds` con las mediciones.

## 4. Escritura mediante API REST

**Método:** POST

**Endpoint:**

`https://api.thingspeak.com/update`

La petición debe incluir la clave de escritura y los valores de los campos.

Ejemplo de cuerpo `application/x-www-form-urlencoded`:

`api_key=TU_WRITE_API_KEY&field1=52.4&field2=96.8&field3=35.2&field4=118.6&field5=42.3`

La clave real de escritura debe mantenerse privada y no almacenarse en GitHub.

Una escritura correcta devuelve un identificador de entrada positivo. Una respuesta `0` indica que el registro no se ha aceptado.

## 5. Prueba realizada

Se realizó una escritura utilizando la primera muestra proporcionada por el profesor.

Valores enviados:

- Carga: 52.4 %
- Estabilidad: 96.8
- Refrigerante: 35.2
- Latencia JARVIS: 118.6 ms
- Consumo de repulsores: 42.3 W

Posteriormente, se ejecutó una consulta HTTP GET al endpoint de lectura.

**Resultado:** se recuperó correctamente el registro `entry_id = 1`, con los cinco valores coincidentes con los enviados.

Esto confirma que el canal acepta registros y permite consultarlos mediante su API REST.

## 6. Restricciones y errores

- Debe respetarse el intervalo mínimo entre actualizaciones permitido por ThingSpeak.
- Una clave de escritura inválida puede provocar que el registro no se almacene.
- Las peticiones pueden fallar por problemas de red o indisponibilidad del servicio.
- Los módulos de lectura y escritura deberán gestionar los errores HTTP, las respuestas vacías y los tiempos de espera.

## 7. Datos de prueba

El archivo `data/reactor_samples.csv` contiene las diez mediciones proporcionadas por el profesor.

Estas muestras se utilizarán durante las pruebas de integración de la aplicación.

## 8. Evidencias

Las capturas de la configuración del canal, su acceso público y las pruebas de la API se conservan en `docs/capturas/`.
