# Guion de la defensa ante la FIFA (20 minutos)

**Pregunta central**: ¿por qué esta combinación de modelos, estructuras, estrategias de distribución y
observabilidad es adecuada para el Fixture 2030 bajo las condiciones planteadas?

**Regla del grupo**: cada afirmación se respalda con algo que se puede abrir en el momento (consulta,
request, panel o archivo del repositorio). Si algo no se midió, se dice.

Recursos: `defensa/presentacion.html` (diapositivas), Grafana (`http://localhost:3000/d/fixture2030`),
Swagger (`http://localhost:8000/docs`), terminal en la raíz del repositorio. Preparación previa en `demo.md`.

> Los nombres de los bloques indican el tema, no quién habla: el grupo reparte los bloques antes de la
> defensa y **todos** deben poder responder sobre cualquier módulo (RNF12).

| Min. | Bloque | Contenido | Se muestra | Respaldo |
|---|---|---|---|---|
| 0:00-2:00 | **1. Problema y decisión general** | El Fixture tiene datos de naturaleza distinta: catálogos (equipos), relaciones (quién jugó contra quién), eventos masivos (comentarios), estado efímero (sesiones), mediciones continuas (estadísticas) y entidades con reglas (partido). Una sola base resolvería bien uno o dos de estos patrones y mal el resto. Decisión: **una base por patrón de acceso**, integradas por una API donde **cada endpoint usa una sola base** | Diapositivas 1-2 | `hito-13-monitoreo/docs/decisiones_de_arquitectura.md` |
| 2:00-6:00 | **2. Arquitectura y responsabilidad de cada base** | Recorrido rápido por las 6 bases: qué guarda, qué consulta la motivó, qué estructura se implementó (tabla de la diapositiva 3). Detenerse en dos: Cassandra (partición `(partido, bucket_5m, shard)`) y Neo4j (recorrido de 3 saltos) | Diapositivas 3-4 | Hitos 4-9 |
| 6:00-9:00 | **3. Distribución, consistencia y fallas** | Qué módulo prioriza disponibilidad (comentarios, sesiones, estadísticas) y cuál consistencia (estado del partido en IRIS). Replicación diseñada vs. laboratorio de un nodo. Qué pasa si se cae una base: solo sus endpoints fallan | Diapositiva 5 | `decisiones_de_arquitectura.md` (tabla CAP) |
| 9:00-13:00 | **4. Operación en vivo** | Dos flujos completos desde Swagger: (a) publicar un comentario y leer el feed (Cassandra + caché Redis); (b) iniciar un partido y ver el 409 al saltear un estado (IRIS). Mostrar en el log el `requestId` y la base | Swagger + terminal | `demo.md` pasos 3-4 |
| 13:00-17:30 | **5. Evidencia: carga, monitoreo y falla** | Hito 12: línea base → cuello de botella (la API en 1 núcleo, no Cassandra) → optimización → resultado medido e integridad verificada. Hito 13: dashboard (disponibilidad, latencia, volumen, errores, comparación de bases) y la prueba de falla de Cassandra (antes / durante / después) | Diapositivas 6-8 + Grafana | `hito-12-.../docs/evidencia/comparacion.md`, `evidencia/prueba_de_falla_*` |
| 17:30-20:00 | **6. Cierre** | Por qué es adecuada, qué trade-offs se aceptaron (6 productos que operar, duplicación, frescura de 1 s en el feed, RF=1 en el laboratorio) y qué se mejoraría (réplicas reales, JMX de Cassandra, caché en más endpoints, Data Mart programado) | Diapositiva 9 | `limitaciones_y_evidencia.md` |

## Qué decir en cada bloque (puntos clave, no texto para leer)

**Bloque 1**
- "No elegimos seis bases para usar seis tecnologías: elegimos un patrón de acceso por tipo de dato".
- "Ninguna request de usuario cruza bases: si se cae una, se degrada un módulo, no la plataforma".

**Bloque 2**
- Cassandra: "un partido caliente en una sola partición sería un punto caliente de escritura; por eso la
  ventana de 5 minutos y los 8 shards".
- Neo4j: "la pregunta *contra quién jugó* son saltos entre nodos; en documental serían lookups encadenados".
- Redis: "TTL de la sesión = expiración sin código; `noeviction` porque preferimos un error visible a
  perder sesiones en silencio".

**Bloque 3**
- "Comentarios: AP. Estado del partido: CP. No es una sola respuesta para todo el sistema".
- "En el laboratorio todo es un nodo: la replicación es diseño, y lo decimos".

**Bloque 4** — si algo falla en vivo, pasar al plan B de `demo.md` (capturas y salidas guardadas).

**Bloque 5**
- "El primer cuello de botella que encontramos fue nuestro propio generador de carga. Lo corregimos antes
  de medir la línea base".
- "Con 60 usuarios la API estaba en 90 % de un núcleo y Cassandra tenía margen: el cuello era la
  integración, no la base".
- "Una mejora sin integridad no cuenta: verificamos cada comentario escrito en las dos tablas".
- En Grafana: explicar cada panel con la pregunta que responde ("¿está arriba?", "¿tarda?", "¿cuánto?",
  "¿falla?", "¿cuál base?").

**Bloque 6**
- "La solución es adecuada porque cada base atiende el patrón que mejor resuelve, las fallas quedan
  aisladas por módulo y lo podemos observar; no porque sea perfecta".

## Reparto sugerido de preguntas probables (6.5)

| Pregunta | Dónde está la respuesta |
|---|---|
| ¿Por qué este modelo para este dato? / ¿Qué consulta sería costosa con otra estructura? | `decisiones_de_arquitectura.md`, sección de cada base |
| ¿Cómo se distribuyen los datos? ¿Qué pasa si cae un nodo o una región? | Tabla CAP; Hito 6 (RF=3, LOCAL_QUORUM, diseño) |
| ¿Dónde está el cuello de botella? ¿Cómo distinguen API de base? | Hito 12 `linea_base.md`: CPU por componente y latencia cliente vs servidor |
| ¿Qué métrica miran primero ante más latencia? | p95 por base y ping por base (dashboard, fila 3) |
| ¿Qué evidencia tienen de que la optimización funcionó? | Hito 12 `comparacion.md` (3 repeticiones por configuración, misma carga) e integridad |
| ¿Qué cambiarían si el tráfico se multiplica? | Más procesos/instancias de la API detrás de un balanceador, caché en más lecturas, réplicas, Cassandra con más nodos |
| ¿Qué se pierde o retrasa durante una falla? | Prueba de falla: comentarios 503 durante la caída; sesiones hasta 1 s (AOF); feed hasta 1 s desactualizado (caché) |
| ¿Qué no pueden afirmar porque no fue medido? | `limitaciones_y_evidencia.md` |
| ¿Qué costo operativo agregan seis productos? | `decisiones_de_arquitectura.md`, última sección |
