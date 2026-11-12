# Stark Reactor IoT Monitor

Aplicación de monitorización de la telemetría del reactor de Stark Industries, desarrollada para la **Actividad 2 (grupal): Integración de sistemas IoT** de la asignatura **Tecnologías Emergentes (UNIR)**.

## Objetivo

Crear un **canal público en ThingSpeak** y una **aplicación ejecutable** que permita enviar y consultar mediciones del reactor mediante la API HTTP de ThingSpeak.

### Variables monitorizadas

| Campo | Parámetro | Unidad / rango indicado |
| --- | --- | --- |
| `field1` | Carga de energía del núcleo | `%` |
| `field2` | Estabilidad del campo | `0–100` |
| `field3` | Flujo de refrigerante de vibranium | `0–100` |
| `field4` | Latencia del protocolo JARVIS | `ms` |
| `field5` | Consumo energético de los repulsores | `W` |

El profesorado facilita **10 muestras experimentales** para validar las operaciones de lectura y escritura. Se usarán como datos de prueba, no como un flujo de sensores reales.

## Enlaces del equipo

- [Tablero de tareas (GitHub Project)](https://github.com/users/Josecp03/projects/2)
- [Guía de tareas y roles](./TASKS.md)
- [Canal público ThingSpeak Iot](https://thingspeak.mathworks.com/channels/3566091)

## Tecnologías propuestas

- **Python 3.11+** para la aplicación.
- **Tkinter** para la interfaz de escritorio.
- **Requests** para las llamadas HTTP a ThingSpeak.
- **Matplotlib** para las gráficas de evolución (mejora adicional, no requisito explícito).
- **pytest** para pruebas automatizadas.

La tecnología está propuesta por el equipo: el enunciado permite elegir el lenguaje siempre que se entregue una aplicación ejecutable o un proyecto de software completo.

## Arquitectura prevista

```text
stark-reactor-iot-monitor/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── services/
│   │   ├── read_service.py
│   │   └── write_service.py
│   ├── ui/
│   │   ├── app.py
│   │   └── history_view.py
│   └── charts/
│       └── reactor_charts.py
├── data/
│   └── reactor_samples.csv
├── tests/
├── docs/
│   └── capturas/
├── .env.example
├── .gitignore
├── requirements.txt
├── TASKS.md
└── README.md
```

**Flujo:** interfaz → servicios de lectura/escritura → API de ThingSpeak → canal público del reactor.

## Instalación y ejecución

Requisitos: **Python 3.11 o superior** con Tkinter (incluido en el instalador oficial de Python para Windows y macOS; en Debian/Ubuntu: `sudo apt install python3-tk`).

1. Clonar el repositorio y entrar en su directorio.
2. Crear y activar un entorno virtual:

   ```bash
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   # .venv\Scripts\Activate.ps1
   ```

3. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Copiar `.env.example` a `.env` y escribir la Write API Key del canal (pestaña *API Keys* de ThingSpeak):

   ```dotenv
   THINGSPEAK_CHANNEL_ID=3566091
   THINGSPEAK_WRITE_API_KEY=REEMPLAZAR
   THINGSPEAK_READ_API_KEY=
   ```

   | Variable | Obligatoria | Uso |
   | --- | --- | --- |
   | `THINGSPEAK_CHANNEL_ID` | Sí | Identificador numérico del canal. Si no se define, se usa `3566091`. |
   | `THINGSPEAK_WRITE_API_KEY` | Sí, para enviar muestras | Clave de escritura del canal. |
   | `THINGSPEAK_READ_API_KEY` | No | Solo necesaria si el canal deja de ser público. |
   | `THINGSPEAK_BASE_URL` | No | URL de la API (por defecto `https://api.thingspeak.com`). |
   | `THINGSPEAK_HTTP_TIMEOUT` | No | Tiempo máximo de espera por petición, en segundos (por defecto `10`). |

   Las variables también pueden definirse directamente en el entorno del sistema; tienen prioridad sobre `.env`. El archivo `.env` está excluido de Git mediante `.gitignore`: nunca subir claves reales al repositorio.

5. Comprobar la configuración (opcional):

   ```bash
   python -m src.main --check-config
   ```

   Muestra el canal y si las claves están configuradas, sin revelar su valor. Termina con código `1` si falta alguna variable obligatoria.

6. Iniciar la aplicación desde la raíz del proyecto:

   ```bash
   python -m src.main
   ```

   Si falta la Write API Key, la aplicación se abre en **modo solo lectura** y muestra un aviso con los pasos para configurarla.

7. Ejecutar las pruebas:

   ```bash
   python -m pytest -v
   ```

## Funcionalidades previstas

- Enviar los cinco parámetros del reactor a ThingSpeak.
- Consultar los registros del canal y mostrar sus fechas y valores.
- Validar entradas numéricas y rangos expresamente definidos.
- Mostrar mensajes de éxito y error.
- Presentar el histórico en una tabla.
- **Mejora opcional:** gráficas de evolución temporal.

**Nota:** deben respetarse los límites y el intervalo mínimo de actualización de ThingSpeak. Las respuestas de su API se validarán; una petición HTTP que retorna correctamente no implica necesariamente que un registro haya sido aceptado.

## Trabajo en equipo

| Rol (label) | Responsabilidad |
| --- | --- |
| `role:platform` | Canal, configuración API y datos de prueba |
| `role:read` | Servicio de consulta de datos |
| `role:write` | Servicio de publicación y validación |
| `role:ui` | Interfaz e integración |
| `role:qa-docs` | Gráficas, pruebas finales y documentación |

### Reglas básicas

- Crear ramas `feature/<numero-issue>-descripcion` o `docs/<numero-issue>-descripcion`.
- Abrir un Pull Request por tarea y enlazarlo con su Issue (`Closes #N`).
- Solicitar al menos una revisión antes de integrar en `main`.
- Mantener credenciales fuera del repositorio y de los logs.
- Cada integrante documenta su parte; la persona de QA/documentación unifica el informe final.

## Entrega académica

El enunciado solicita **dos archivos**: un documento editable con la memoria y un archivo ZIP con el código fuente y demás ficheros, incluida la hoja de control grupal. Todos los integrantes deben entregar los mismos documentos en el aula virtual.

La memoria debe incluir la identificación del canal, el autor, las peticiones API, la evidencia de que es público, capturas del funcionamiento y pasos de instalación/configuración. Extensión máxima: **15 páginas** (sin portada, índice y anexos); **Calibri 12**, interlineado **1,5**.

La rúbrica asigna **20 %** al canal, **60 %** al funcionamiento de la aplicación y **20 %** a las pautas y al formato de entrega.
