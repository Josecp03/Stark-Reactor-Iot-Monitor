# Tareas para GitHub Issues — Stark Reactor IoT Monitor

## Configuración recomendada del GitHub Project

**Columnas:** `To do`, `Doing`, `In review`, `Done`.

**Labels de rol:** `role:platform`, `role:read`, `role:write`, `role:ui`, `role:qa-docs`.

## Persona 1 — `role:platform` — Plataforma ThingSpeak y datos

### P1-01 · Configurar canal ThingSpeak con los cinco campos
- Crear un canal para el reactor Arc.
- Asignar `field1` carga (%), `field2` estabilidad (0–100), `field3` refrigerante (0–100), `field4` latencia JARVIS (ms), `field5` consumo de repulsores (W).
- **Criterio de aceptación:** los cinco campos aparecen correctamente identificados en el canal.
- **Prioridad:** Alta.

### P1-02 · Habilitar acceso público y documentar API
- Configurar el canal como público.
- Registrar Channel ID, Author, URL de lectura y estructura de URL de escritura.
- Capturar las evidencias solicitadas sin exponer el valor de la Write API Key.
- **Criterio de aceptación:** se puede consultar el canal público y existen evidencias de su configuración.
- **Depende de:** P1-01. **Prioridad:** Alta.

### P1-03 · Preparar las 10 muestras del profesor
- Transcribir los diez registros originales de los cinco campos a `data/reactor_samples.csv`.
- Revisar decimales, orden de campos y que haya exactamente diez filas de datos.
- **Criterio de aceptación:** CSV validado contra la tabla de la temática, sin alteración de valores.
- **Prioridad:** Alta.

### P1-04 · Probar API manualmente y entregar guía técnica
- Hacer al menos una escritura y lectura utilizando herramientas HTTP.
- Documentar un ejemplo de petición, la respuesta esperada y los errores observables.
- Coordinar límites de frecuencia y proporcionar a lectura/escritura los identificadores y esquema necesarios.
- **Criterio de aceptación:** una muestra enviada se recupera del canal, con prueba reproducible y claves protegidas.
- **Depende de:** P1-02. **Prioridad:** Alta.

### P1-05 · Apoyar integración y carga de muestras
- Ayudar a probar las diez muestras a través de la aplicación y contrastarlas con ThingSpeak.
- Comprobar que se respeta el intervalo mínimo permitido entre escrituras.
- **Criterio de aceptación:** existe registro de pruebas sobre el canal real para las diez muestras.
- **Depende de:** P3-03, P4-04. **Prioridad:** Media.

## Persona 2 — `role:read` — Consulta y lectura

### P2-01 · Definir contrato de datos de lectura
- Acordar con UI la estructura que devolverá el servicio (fecha, ID del registro y cinco campos).
- Definir tratamiento de valores nulos, respuesta vacía y errores.
- **Criterio de aceptación:** contrato de función documentado y aprobado por UI.
- **Prioridad:** Alta.

### P2-02 · Implementar servicio GET de feeds
- Consultar `channels/{id}/feeds.json` mediante Requests.
- Configurar timeouts y tratamiento de fallos HTTP/JSON.
- **Criterio de aceptación:** lectura de registros reales desde el canal público.
- **Depende de:** P1-02, P2-01. **Prioridad:** Alta.

### P2-03 · Transformar respuesta JSON a registros de dominio
- Extraer `created_at`, `entry_id` y los cinco `fieldN`.
- Preparar una lista apta para mostrar en la tabla/gráficas.
- **Criterio de aceptación:** se mantienen las correspondencias exactas entre campo y variable.
- **Depende de:** P2-02. **Prioridad:** Alta.

### P2-04 · Probar consultas y documentar el módulo
- Añadir pruebas de JSON correcto, canal vacío, fallo HTTP, timeout y campos nulos.
- Documentar cómo usar el servicio desde la UI.
- **Criterio de aceptación:** pruebas automatizadas ejecutables y ejemplo de uso.
- **Depende de:** P2-03. **Prioridad:** Media.

## Persona 3 — `role:write` — Escritura y validaciones

### P3-01 · Definir contrato de escritura y reglas de validación
- Acordar la firma del servicio para los cinco parámetros.
- Validar los cinco datos como numéricos; rangos 0–100 para estabilidad y refrigerante.
- No inventar límites críticos obligatorios no definidos por el documento.
- **Criterio de aceptación:** reglas y errores documentados para integrarlos con la UI.
- **Prioridad:** Alta.

### P3-02 · Implementar servicio de envío a ThingSpeak
- Enviar los cinco campos utilizando la Write API Key desde configuración local.
- Añadir timeout y tratamiento de errores.
- Comprobar respuesta de aceptación (no considerar válido `0`).
- **Criterio de aceptación:** una petición válida crea un registro real en el canal.
- **Depende de:** P1-02, P3-01. **Prioridad:** Alta.

### P3-03 · Controlar intervalo entre escrituras y retorno de resultados
- Evitar envíos que incumplan el intervalo mínimo del plan de ThingSpeak.
- Devolver a la UI un resultado explícito de éxito o error.
- **Criterio de aceptación:** los rechazos y las escrituras correctas se muestran de forma diferenciada.
- **Depende de:** P3-02. **Prioridad:** Alta.

### P3-04 · Probar escritura y documentar el módulo
- Crear tests para valores válidos, vacíos, texto no numérico, rango incorrecto, fallo HTTP y respuesta `0`.
- Documentar ejemplos de consumo del servicio.
- **Criterio de aceptación:** pruebas automatizadas que no publiquen accidentalmente datos durante su ejecución normal.
- **Depende de:** P3-03. **Prioridad:** Media.

## Persona 4 — `role:ui` — Interfaz e integración

### P4-01 · Crear estructura del proyecto y entorno
- Crear paquetes `src/`, `services/`, `ui/`, `charts/`, `data/`, `tests/`.
- Añadir `requirements.txt`, `.gitignore`, `.env.example` y punto de entrada.
- Establecer cómo se cargarán variables de entorno locales.
- **Criterio de aceptación:** aplicación base arranca en un entorno limpio.
- **Prioridad:** Alta.

### P4-02 · Diseñar formulario del reactor
- Crear cinco entradas correctamente etiquetadas y botones de enviar/consultar.
- Mostrar errores de entrada y mensajes de estado.
- **Criterio de aceptación:** interfaz navegable sin API conectada y sin bloquearse por validaciones.
- **Depende de:** P4-01. **Prioridad:** Alta.

### P4-03 · Añadir tabla de histórico
- Mostrar fecha/registro y cinco valores con sus unidades.
- Contemplar canal vacío y errores recuperables.
- **Criterio de aceptación:** tabla renderiza resultados de prueba y admite refresco.
- **Depende de:** P4-02, P2-01. **Prioridad:** Alta.

### P4-04 · Integrar lectura y escritura reales
- Conectar botones a los servicios de las personas 2 y 3.
- Evitar congelar la ventana durante peticiones de red.
- Confirmar el flujo envío → consulta → visualización.
- **Criterio de aceptación:** aplicación ejecutable de extremo a extremo con ThingSpeak.
- **Depende de:** P2-03, P3-03, P4-03. **Prioridad:** Alta.

## Persona 5 — `role:qa-docs` — Gráficas, QA y entrega

### P5-01 · Elaborar plan y matriz de pruebas
- Definir casos de lectura, escritura, validaciones, canal vacío, fallos HTTP y funcionamiento general.
- Establecer resultados esperados para las diez muestras.
- **Criterio de aceptación:** matriz de pruebas lista antes de la integración.
- **Prioridad:** Alta.

### P5-02 · Implementar visualización de evolución
- Crear gráfica temporal para carga del núcleo y estabilidad del campo, usando datos del servicio de lectura.
- Integrarla con la UI coordinándose con la persona 4.
- **Criterio de aceptación:** gráfica muestra puntos reales y no falla con datos vacíos.
- **Depende de:** P2-03, P4-03. **Prioridad:** Media. **Mejora opcional**.

### P5-03 · Ejecutar QA de extremo a extremo
- Ejecutar el flujo real de envío/consulta de las diez muestras y comprobar correspondencia exacta.
- Documentar fallos, capturas y correcciones verificadas.
- **Criterio de aceptación:** evidencia de pruebas y lista de incidencias cerradas o conocidas.
- **Depende de:** P4-04, P1-05. **Prioridad:** Alta.

### P5-04 · Unificar memoria académica
- Recibir de cada persona explicación y capturas de su módulo.
- Incluir configuración pública del canal, Channel ID/Author/URLs API, operaciones, instalación, capturas y resultados.
- Aplicar Calibri 12, interlineado 1,5 y máximo de 15 páginas sin portada/índice/anexos.
- **Criterio de aceptación:** documento editable completo y revisado contra el enunciado.
- **Depende de:** P1-02, P2-04, P3-04, P5-03. **Prioridad:** Alta.

### P5-05 · Preparar ZIP y checklist de entrega
- Incluir código fuente, dependencias, README, datos necesarios y hoja de control grupal.
- Excluir `.env`, claves privadas, `.venv`, cachés y otros ficheros locales.
- Verificar que todos entregarán los mismos dos archivos y denominación exigida.
- **Criterio de aceptación:** ZIP instalable en limpio y documentos finales listos para el aula virtual.
- **Depende de:** P5-04. **Prioridad:** Alta.
