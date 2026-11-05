# Plan de tareas actualizado — Stark Reactor IoT Monitor

Actualizado tras la explicación de la Actividad 2 en la Clase 9 de Tecnologías Emergentes (UNIR).

## Requisitos confirmados por el profesor

- Crear un canal ThingSpeak para la temática del reactor Arc, con los cinco campos definidos en «Temática Actividad 2», y hacerlo público.
- Entregar Channel ID, Author, direcciones API y evidencias de configuración.
- Implementar una aplicación o proyecto de software completo, no un notebook o entorno experimental.
- Permitir **introducir manualmente** los cinco valores y enviarlos al canal. La importación CSV o la generación automática pueden añadirse, pero **no sustituyen la entrada manual**.
- Permitir leer y presentar los registros desde ThingSpeak mediante la API.
- Dejar el canal y la conexión fáciles de configurar/ejecutar para la evaluación. Proteger la Write API Key: no publicarla en Git ni en documentación.
- Respetar el intervalo entre escrituras permitido por ThingSpeak (en clase se comenta 15 s).
- Dar prioridad al funcionamiento, la organización del código, la usabilidad, las instrucciones de instalación y las evidencias. Las gráficas son una mejora optativa.
- Entregar memoria editable y ZIP con código fuente, instrucciones y hoja de control grupal. El enlace a GitHub puede complementar la entrega, pero no reemplaza el ZIP exigido por el enunciado.

## Metadatos para GitHub

**Etiquetas de rol:** `role:platform`, `role:read`, `role:write`, `role:ui`, `role:qa-docs`.

**Otras etiquetas sugeridas:** `type:feature`, `type:test`, `type:docs`, `type:chore`, `priority:high`, `priority:medium`, `priority:low`.

**Estados del Project:** Backlog, Ready, In progress, In review, Done. Usar `blocked` como etiqueta opcional para dependencias.

## Persona 1 — `role:platform` — Plataforma ThingSpeak y datos

### P1-01 · Configurar el canal ThingSpeak con los cinco campos
- Crear el canal de monitorización del reactor Arc.
- Configurar `field1` carga del núcleo (%), `field2` estabilidad del campo (0–100), `field3` flujo de refrigerante (0–100), `field4` latencia JARVIS (ms), `field5` consumo de repulsores (W).
- **Aceptación:** el canal existe y los cinco campos se ven correctamente en Channel Settings.
- **Prioridad:** Alta. **Estado actual:** Hecho (según las pruebas compartidas).

### P1-02 · Habilitar el acceso público y documentar la API
- Activar `Share channel with everyone`.
- Registrar Channel ID, Author, URL pública de lectura y estructura de petición de escritura sin divulgar las claves.
- Guardar capturas de Channel Settings, Sharing y API Requests con las credenciales ocultas.
- **Aceptación:** el canal es consultable sin autenticación y las evidencias están en `docs/`.
- **Dependencia:** P1-01. **Prioridad:** Alta. **Estado actual:** Hecho si ya están las capturas y documentación.

### P1-03 · Preparar y verificar las diez muestras del profesor
- Transcribir los diez registros a `data/reactor_samples.csv`, con cabecera `field1,field2,field3,field4,field5`.
- Comprobar el número de filas, el orden de las columnas y todos los valores contra «Temática Actividad 2».
- Especificar que son datos de validación y no una carga inicial obligatoria.
- **Aceptación:** CSV versionado, con diez registros fieles al original.
- **Prioridad:** Alta. **Estado actual:** Hecho si ya está verificado y subido.

### P1-04 · Validar y documentar la comunicación HTTP con ThingSpeak
- Probar al menos una escritura real y una lectura real; registrar los endpoints y el resultado obtenido.
- Incluir en `docs/thingspeak-api.md` un ejemplo reproducible con placeholders para las claves, posibles respuestas de error y la restricción de intervalo entre inserciones.
- Preparar `.env.example`, `.gitignore` y la explicación de configuración local; confirmar que la clave expuesta anteriormente fue rotada.
- **Aceptación:** una muestra enviada se recupera con sus cinco valores y un compañero puede repetir la prueba siguiendo la guía, sin consultar secretos en GitHub.
- **Dependencia:** P1-02. **Prioridad:** Alta. **Estado actual:** Casi/Hecho, pendiente de comprobar credenciales y guía.

### P1-05 · Ayudar en las pruebas de integración con el canal real
- Colaborar con las personas 3, 4 y 5 para comprobar escritura **manual** y lectura desde la aplicación.
- Validar con las diez muestras del CSV y respetar la cadencia de escritura; registrar resultados y problemas.
- Confirmar que el canal sigue siendo público durante la evaluación.
- **Aceptación:** evidencia de pruebas de extremo a extremo y coincidencia de valores, con errores detectados documentados.
- **Dependencias:** P3-03, P4-04. **Prioridad:** Media. **Estado actual:** Bloqueado hasta integración.

## Persona 2 — `role:read` — Integración de lectura

### P2-01 · Definir el contrato de datos de lectura
- Acordar con personas 4 y 5 la interfaz del módulo de lectura y un modelo con `created_at`, `entry_id` y los cinco campos.
- Definir cómo tratar nulos, cadenas numéricas y canales sin registros.
- **Aceptación:** contrato documentado y aprobado por quien integra la interfaz.
- **Prioridad:** Alta.

### P2-02 · Implementar peticiones GET a ThingSpeak
- Consultar feeds del canal configurable mediante HTTP GET y timeout.
- Permitir obtener los últimos N registros e informar de códigos HTTP y errores de conexión.
- **Aceptación:** módulo que lee registros reales sin depender de la interfaz.
- **Dependencia:** P2-01. **Prioridad:** Alta.

### P2-03 · Normalizar la respuesta JSON para la interfaz
- Transformar `feeds` en registros ordenados con marcas temporales y valores numéricos cuando existan.
- Mantener los cinco campos correctamente mapeados y contemplar valores vacíos.
- **Aceptación:** devuelve estructuras estables que la tabla puede mostrar sin conocer la API.
- **Dependencia:** P2-02. **Prioridad:** Alta.

### P2-04 · Probar y documentar la lectura
- Crear tests con respuesta válida, sin registros, campos ausentes y fallo de red/API.
- Proporcionar ejemplos de salida, documentación de uso y capturas de lectura real para la memoria.
- **Aceptación:** pruebas reproducibles y lectura verificada con el canal `3566091`.
- **Dependencias:** P2-02 y P2-03. **Prioridad:** Media.

## Persona 3 — `role:write` — Integración de escritura

### P3-01 · Definir el contrato de escritura y la validación de valores
- Definir función que reciba los cinco campos introducidos **manualmente** por el usuario.
- Comprobar que son valores numéricos; estabilidad y refrigerante deben estar en 0–100. No inventar rangos máximos para campos cuyo documento no los concreta.
- Acordar formato de resultados y errores con la persona 4.
- **Aceptación:** contrato documentado y validaciones probadas con casos válidos e inválidos.
- **Prioridad:** Alta.

### P3-02 · Implementar envío de muestras a ThingSpeak
- Enviar los cinco campos por la API de escritura con clave obtenida del entorno, nunca hardcodeada.
- Usar timeout; comprobar tanto errores HTTP como respuesta `0` de ThingSpeak.
- **Aceptación:** una muestra introducida manualmente desde el formulario se guarda en el canal real.
- **Dependencia:** P3-01. **Prioridad:** Alta.

### P3-03 · Controlar el intervalo entre escrituras y errores
- Evitar múltiples clics y nuevas peticiones antes del tiempo mínimo (en clase se comenta 15 s; usar configuración conservadora si procede).
- Informar al usuario de cuánto falta para otra escritura; no prometer éxito hasta comprobar respuesta.
- **Aceptación:** dos envíos consecutivos no provocan duplicados ni fallos silenciosos por exceso de frecuencia.
- **Dependencia:** P3-02. **Prioridad:** Alta.

### P3-04 · Probar y documentar la escritura
- Probar primera muestra, campos inválidos, respuesta `0`, timeout y cadencia de envío.
- Documentar un ejemplo reproducible y facilitar evidencias de la escritura manual para la memoria.
- **Aceptación:** pruebas documentadas y evidencia de inserción y recuperación del mismo registro.
- **Dependencias:** P3-02 y P3-03. **Prioridad:** Media.

## Persona 4 — `role:ui` — Aplicación, UX e integración

### P4-01 · Preparar el proyecto ejecutable y la configuración inicial
- Crear punto de entrada `src/main.py`, dependencias (`requirements.txt`) y carga de configuración desde `.env`.
- Asegurar que el proyecto pueda ejecutarse desde terminal con una instrucción clara; informar de credenciales faltantes sin mostrar secretos.
- **Aceptación:** aplicación inicia en un entorno limpio siguiendo el README, sin notebook ni servidor adicional obligado.
- **Prioridad:** Alta.

### P4-02 · Crear interfaz para introducir manualmente las cinco variables
- Diseñar un formulario con cinco campos etiquetados con unidades, botón `Enviar` y mensajes claros de validación/resultado.
- El formulario debe permitir introducir cualquier muestra válida sin depender del CSV ni de un generador.
- **Aceptación:** el profesor puede escribir los cinco valores a mano y enviar una muestra siguiendo indicaciones mínimas.
- **Dependencias:** P3-01 y P4-01. **Prioridad:** Muy alta.

### P4-03 · Crear vista de consulta e histórico
- Añadir botón `Consultar/Actualizar` y tabla con fecha/identificador y los cinco valores.
- Mostrar estado de carga, ausencia de datos y errores de comunicación de forma entendible.
- **Aceptación:** al consultar se muestran los últimos registros reales del canal con sus unidades y nombres.
- **Dependencias:** P2-01 y P4-01. **Prioridad:** Alta.

### P4-04 · Integrar lectura/escritura y revisar usabilidad
- Conectar la UI a los servicios de las personas 2 y 3 sin duplicar lógica de red.
- Confirmar configuración del canal, escritura manual, lectura posterior, bloqueo temporal de envíos y mensajes de error.
- Revisar que la interfaz se pueda utilizar sin leer un manual extenso.
- **Aceptación:** flujo completo de escribir manualmente → confirmar en ThingSpeak → consultar → ver registro; aplicación reproducible con instrucciones.
- **Dependencias:** P2-03, P3-03, P4-02 y P4-03. **Prioridad:** Muy alta.

## Persona 5 — `role:qa-docs` — Calidad, UX y entrega

### P5-01 · Diseñar matriz de pruebas y criterios de aceptación
- Definir pruebas para canal público, lectura, escritura manual, cinco campos, datos vacíos, errores HTTP, frecuencia y configuración inicial.
- Preparar matriz que relacione pruebas con requisitos y rúbrica del profesor.
- **Aceptación:** plan ejecutable antes de la integración con resultados esperados claros.
- **Prioridad:** Alta.

### P5-02 · Revisar usabilidad y, si hay margen, añadir visualizaciones
- Realizar revisión de facilidad de uso, legibilidad, nombres, unidades, feedback, errores y navegación.
- Abrir incidencias concretas cuando algo impida al profesor probar la aplicación.
- **Opcional:** gráficas de evolución del reactor, sin comprometer las funciones obligatorias.
- **Aceptación:** checklist UX completado y correcciones verificadas; gráfica solo si se aprueba como mejora.
- **Dependencia:** P4-02 y P4-03. **Prioridad:** Alta para UX, Baja para gráficas.

### P5-03 · Ejecutar pruebas de extremo a extremo
- Verificar escritura manual de datos reales, lectura desde ThingSpeak y coincidencia de los diez registros de prueba.
- Comprobar manejo de errores y la frecuencia de actualización con los responsables de cada módulo.
- Guardar evidencias y registrar incidencias/resoluciones.
- **Aceptación:** matriz de pruebas ejecutada, errores críticos resueltos y capturas del flujo completo.
- **Dependencias:** P4-04, P1-05. **Prioridad:** Alta.

### P5-04 · Preparar la memoria académica y el manual mínimo
- Unificar textos que aporta cada persona: canal, autor, endpoints, desarrollo, funcionamiento, capturas, pruebas y prerequisitos.
- Incluir instrucciones claras de instalación/configuración y uso de cada botón u opción, sin divulgar claves.
- Aplicar formato UNIR: Calibri 12, interlineado 1,5 y máximo 15 páginas (sin portada, índice ni anexos).
- **Aceptación:** documento editable, coherente, legible y verificable por el profesor.
- **Dependencia:** evidencias de todo el equipo. **Prioridad:** Alta.

### P5-05 · Preparar ZIP, hoja de control y revisión de entrega
- Empaquetar código fuente, CSV, `requirements.txt`, `.env.example`, README y documentación necesaria; excluir `.env` real y secretos.
- Revisar instalación y ejecución desde una copia limpia; comprobar que el código está dentro del ZIP aunque también exista GitHub.
- Incorporar hoja de control grupal; revisar nomenclaturas de DOCX y ZIP y confirmar entrega individual de todos los integrantes.
- **Aceptación:** ZIP reproducible sin claves expuestas, memoria final y hoja grupal preparados conforme al enunciado.
- **Dependencias:** P5-03 y P5-04. **Prioridad:** Muy alta.

## Orden de ejecución recomendado

1. **Ya realizados por plataforma:** P1-01, P1-02, P1-03; cerrar P1-04 y comprobar rotación de cualquier clave antes expuesta.
2. **Acordar contratos entre módulos:** P2-01 y P3-01, con participación de P4.
3. **Trabajo en paralelo:** P2-02/03, P3-02/03, P4-01/02/03, P5-01.
4. **Integración:** P4-04; después P1-05, P2-04, P3-04, P5-02/03.
5. **Entrega:** P5-04 y P5-05, con aportaciones y revisión de todos.

## Definition of Done de un Issue

- Implementación o documento subido al repositorio mediante PR revisada.
- Criterios de aceptación verificados.
- Sin secretos ni claves reales en commits, capturas o logs.
- Tests y evidencias adjuntos cuando corresponda.
- Instrucciones actualizadas si cambia el uso o instalación.
