# Stark Reactor IoT Monitor

Aplicación de escritorio en Python y Tkinter para la **Actividad 2 grupal de Tecnologías Emergentes (UNIR)**. Permite enviar mediciones del reactor Arc a ThingSpeak y consultar los últimos registros del canal.

## Instalación en Windows

Abre **PowerShell** en la carpeta que contiene `requirements.txt`. Necesitas Python 3.11 o superior con Tkinter y conexión a Internet. Ejecuta cada comando por separado.

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si es la primera vez que configuras el proyecto, crea el archivo local de configuración.

```powershell
Copy-Item .env.example .env
```

Abre `.env` en tu editor y sustituye `REEMPLAZAR` en `THINGSPEAK_WRITE_API_KEY` por la clave de escritura vigente de la pestaña **API Keys** del canal. Si ya tienes un `.env` configurado, úsalo directamente.

| Variable | Configuración |
| --- | --- |
| `THINGSPEAK_CHANNEL_ID` | Identificador del canal. El valor por defecto es `3566091`. |
| `THINGSPEAK_WRITE_API_KEY` | Necesaria para enviar muestras. |
| `THINGSPEAK_READ_API_KEY` | Puede quedar vacía para el canal público. |
| `THINGSPEAK_BASE_URL` | Por defecto, `https://api.thingspeak.com`. |
| `THINGSPEAK_HTTP_TIMEOUT` | Tiempo de espera por petición, en segundos. Por defecto, `10`. |

Las variables de entorno del sistema tienen prioridad sobre `.env`. Guarda las claves reales en la configuración local y comparte la clave de escritura con el evaluador por un canal privado si la necesita para probar el envío.

## Arranque y comprobaciones

Desde la raíz del proyecto, abre la aplicación con este comando.

```powershell
.\.venv\Scripts\python.exe -m src.main
```

Con el canal público y sin clave de escritura, se puede consultar el histórico en modo solo lectura.

Para comprobar la configuración local sin abrir la ventana ni mostrar las claves, usa:

```powershell
.\.venv\Scripts\python.exe -m src.main --check-config
```

Para ejecutar las pruebas automatizadas, usa:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas simulan la API de ThingSpeak. Las pruebas de interfaz necesitan que Tkinter pueda abrir una ventana.

En macOS o Linux usa `python3 -m venv .venv`, `cp .env.example .env` si todavía no tienes el archivo y `.venv/bin/python` en los comandos del entorno virtual. En Debian o Ubuntu, instala `python3-tk` si falta Tkinter.

## Uso

1. En **Enviar muestra**, escribe los cinco valores. Se admite coma o punto decimal. **Rellenar** copia al formulario una muestra de prueba y **Limpiar** vacía los campos.
2. Pulsa **Enviar**. Al guardar, aparece el número de registro y el botón muestra la espera hasta el siguiente envío.
3. Abre **Histórico**, elige cuántos registros quieres ver y pulsa **Consultar / Actualizar**. Busca el mismo número de registro para comprobar los valores guardados.

| Campo | Medición | Unidad o rango |
| --- | --- | --- |
| `field1` | Carga de energía del núcleo | % |
| `field2` | Estabilidad del campo | 0–100 |
| `field3` | Flujo de refrigerante de vibranium | 0–100 |
| `field4` | Latencia del protocolo JARVIS | ms |
| `field5` | Consumo energético de los repulsores | W |

Las diez muestras del profesorado están en [data/reactor_samples.csv](data/reactor_samples.csv).

## Código y documentación

- [src/main.py](src/main.py) arranca la aplicación y [src/config.py](src/config.py) carga la configuración.
- [src/ui](src/ui) contiene el formulario y el histórico. [src/services](src/services) hace las peticiones a ThingSpeak.
- [src/validation.py](src/validation.py) contiene las reglas de validación que comparten el formulario y el servicio de escritura.
- [Integración con ThingSpeak](docs/thingspeak-api.md), [capturas](docs/capturas) y [plan del equipo](TASKS.md).

## Entrega académica

Entrega una memoria editable y un ZIP con el código fuente, `.env.example`, las instrucciones y la hoja de control grupal. Mantén `.env` y `.venv` fuera del ZIP. Todos los integrantes deben entregar los mismos archivos.

En la memoria incluye el ID del canal, su autor, las peticiones de la API, la evidencia de acceso público y un mini manual con capturas de escritura y lectura. Usa Calibri 12, interlineado 1,5 y un máximo de 15 páginas de contenido, sin contar portada, índice ni anexos.
