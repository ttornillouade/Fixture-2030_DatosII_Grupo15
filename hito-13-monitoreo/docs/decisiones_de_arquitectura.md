# Decisiones de arquitectura: por qué esta combinación de bases (RF14, RF15, 6.4)

Este documento es la base técnica de la defensa. Para cada base: qué guarda, qué acceso motivó la
elección, qué estructura se implementó, cómo escala, qué consistencia necesita, qué pasa si se cae, qué
costo introduce y **qué evidencia del repositorio lo respalda**. Se distingue lo implementado y medido
(laboratorio, un nodo por base) de lo diseñado para producción (no medido).

## Visión general

```
                 ┌──────────────────────────── API FastAPI (hito-10-api) ───────────────────────────┐
  usuarios ───▶  │ un endpoint por caso de uso · un adaptador por base · timeout 3 s · /metrics     │
                 └──┬──────────┬───────────┬────────────┬─────────────┬─────────────┬───────────────┘
                    │          │           │            │             │             │
                 MongoDB     Neo4j     Cassandra      Redis       InfluxDB        IRIS
                 equipos y   quién     comentarios   sesiones    estadísticas    partido +
                 jugadores   jugó con  por partido   (TTL) +     por segundo     eventos
                 (docs)      quién     y por usuario caché feed  (series)        (objetos+SQL)
                    └──────────┴───────────┴────── Prometheus + Grafana (hito-13) ─┘
```

**Decisión transversal**: cada endpoint consulta **una sola base** (Hito 10). No hay consultas que crucen
seis bases en tiempo real: eso sería un antipatrón de latencia y de disponibilidad (la request fallaría si
falla cualquiera de las seis). Las preguntas que sí necesitan cruzar fuentes van a una proyección
analítica alimentada por ETL (Hito 12, `integracion_data_mart.md`).

## Base por base

### MongoDB — documental

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Qué guarda | Equipos (64) y jugadores (1.536) | `hito-4-mongodb/` |
| Acceso que la motivó | Ficha de equipo por código; plantel por equipo y posición, ordenado por dorsal, paginado | `GET /equipos/{codigo}`, `GET /jugadores` |
| Estructura | Colecciones `equipos` y `jugadores` con validación `$jsonSchema`, índice único `{equipoId, dorsal}` e índice `{equipoId, posicion, dorsal}`; paginación por clave (sin `skip`) | `hito-4-mongodb/scripts/01_validacion.js`, `05_indices_rendimiento.js` |
| Escala | Diseño: replica set de 3 miembros (lecturas desde secundarios para fichas), sharding por `equipoId` solo si el catálogo creciera mucho (no hace falta: son miles de documentos) | Hito 3 (diseño), `hito-4-mongodb/README.md` (laboratorio: una instancia) |
| Consistencia | Fuerte para la ficha (se edita poco); lecturas desde secundarios aceptables con segundos de retraso | — |
| Si se cae | 503 en `/equipos` y `/jugadores`; el resto de la API sigue | Hito 11 `diagnostico_de_fallas.md` |
| Costo | Jugadores por referencia (`jugadores.equipoId → equipos._id`), no embebidos: no hay integridad referencial del motor (se controla con un script) y la ficha con plantel son dos lecturas | `hito-4-mongodb/docs/decisiones_documentales.md` |

### Neo4j — grafo

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Qué guarda | Jugadores, equipos, partidos, sedes y eventos como nodos; `PERTENECE_A`, `PARTICIPA_EN`, `DISPUTA` como relaciones | `hito-5-neo4j/queries/estructura.cypher` |
| Acceso que la motivó | "¿En qué partidos jugó este jugador y contra quién?" y recorridos de varios saltos (rivales conectados por partidos compartidos; consultas de tres relaciones consecutivas) | `GET /jugadores/{codigo}/partidos`, `hito-5-neo4j/docs/modelo_grafo.md` |
| Por qué no otra base | En documental o relacional, cada salto es un join/lookup; el costo crece con la profundidad. En el grafo, el recorrido sigue punteros (adyacencia sin índice) | `hito-5-neo4j/docs/modelo_grafo.md` |
| Escala | Lecturas: réplicas de lectura (cluster causal en Enterprise). Escrituras: bajas (el grafo cambia con cada partido) | Diseño; laboratorio Community de un nodo |
| Consistencia | Fuerte en el líder; eventual aceptable en réplicas de lectura (consultas de exploración) | — |
| Si se cae | 503 solo en la ruta de relaciones | Hito 11 |
| Costo | Duplica identificadores y algunos atributos de MongoDB; hay que mantener la carga sincronizada | `modelo_grafo.md` |

### Cassandra — columnar distribuida

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Qué guarda | Comentarios de los usuarios por partido y por usuario | `Grupo_15_Hito_6_.../scripts/esquema.cql` |
| Acceso que la motivó | Escrituras masivas durante el partido y lectura del feed reciente; "mis comentarios" | `GET`/`POST /partidos/{codigo}/comentarios` |
| Estructura | `comentarios_por_partido` con partición `(partido_id, bucket_5m, shard)` y clustering `(creado_en DESC, comentario_id DESC)`; `comentarios_por_usuario` con partición `(autor_id, dia_bucket)`. Las dos se escriben en un `BATCH LOGGED` | `decisiones_de_particionamiento.md` |
| Por qué los 8 shards | Un partido caliente concentraría todas las escrituras de 5 minutos en una partición (y un nodo). Con 8 shards se reparten | Hito 6 |
| Escala | Horizontal: más nodos = más particiones repartidas por token. Diseño: RF=3 por datacenter, `LOCAL_QUORUM` | Hito 6 README (laboratorio RF=1) |
| Consistencia | Eventual aceptable para el feed (un comentario puede aparecer 1-2 s tarde). Moderación necesitaría `QUORUM` | `coherencia_tpo.md` del Hito 6 |
| Si se cae | Con RF=1 (laboratorio): no se leen ni publican comentarios, el resto de la API sigue. **Medido** en la prueba de falla de este hito | `evidencia/prueba_de_falla_cassandra_*` |
| Costo | Duplicación (dos tablas); la lectura cuesta 8 consultas + fusión en la API. **Medido en el Hito 12: la fusión en Python fue el cuello de botella** con 60 usuarios | `hito-12-carga-optimizacion/docs/linea_base.md` |

### Redis — clave-valor en memoria

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Qué guarda | Sesiones de usuario (`fixture2030:session:{id}`, HASH con TTL de 30 min) y, desde el Hito 12, la caché de la primera página del feed (TTL 1 s) | Hito 7, `app/adaptadores/cache_comentarios.py` |
| Acceso que la motivó | Lectura por clave en cada request autenticada; expiración automática | `GET`/`DELETE /sesiones/{id}` |
| Estructura | HASH por sesión con `EXPIRE`; STRING JSON por página cacheada con `PX` | Hito 7 |
| Escala | Memoria: 256 MB con `noeviction` (preferimos rechazar escrituras a perder sesiones en silencio). Diseño: Redis Cluster o réplicas + Sentinel | `memoria_y_escalabilidad.md` del Hito 7 |
| Consistencia / durabilidad | AOF `everysec`: ante una caída se puede perder ~1 s de sesiones (el usuario vuelve a iniciar sesión). La caché no necesita durabilidad | Hito 7 |
| Si se cae | Sesiones: 503. Caché: la API vuelve a leer Cassandra (la caché nunca hace fallar una request) | `cache_comentarios.py` |
| Costo | Memoria; frescura acotada (la página del feed puede tener hasta 1 s de atraso) | Hito 12 |

### InfluxDB 3 — series temporales

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Qué guarda | Estadísticas por equipo y por segundo (posesión, pases, tiros) | `hito-8-influxdb/` |
| Acceso que la motivó | Ventanas de tiempo de un partido, crudas o agregadas por minuto | `GET /partidos/{codigo}/estadisticas` |
| Estructura | Tabla `estadisticas_equipo` con tags `partido_id`, `equipo_id`; base `fixture2030_vivo` con retención de 14 días; agregados por minuto | `modelo_multidimensional.md`, `retencion_y_granularidad.md` |
| Escala | Las series son pocas (partido × equipo); crecen los puntos. La retención acota el volumen; los agregados quedan más tiempo | `cardinalidad_y_escalabilidad.md` |
| Consistencia | Eventual aceptable (estadísticas en vivo, segundos de retraso) | — |
| Si se cae | 503 en estadísticas; el resto sigue | Hito 11 |
| Costo | Un producto más que operar; la API limita las ventanas (15 min crudo, 3 h por minuto) para no leer todo el partido | `app/servicios.py` |

### IRIS — multimodelo

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Qué guarda | El partido como entidad compleja con sus eventos (relación padre-hijo) y su estado | `hito-9-iris/scripts/Fixture/*.cls` |
| Acceso que la motivó | Leer el partido completo con sus eventos en una operación y aplicar transiciones de estado validadas (`PROGRAMADO → EN_JUEGO → FINALIZADO`) | `GET /partidos/{codigo}/detalle`, `PATCH /estado` |
| Por qué | Las mismas clases se usan como objetos (reglas de negocio en la clase) y por SQL (consultas) sin duplicar el modelo | Hito 9 |
| Escala | Mirroring (réplica síncrona) para alta disponibilidad; ECP para escalar lecturas (diseño) | Diseño |
| Consistencia | **Fuerte**: el estado del partido no puede ser eventual (no puede haber dos transiciones contradictorias) | 409 ante transición ilegal |
| Si se cae | 503 en detalle y estado del partido | Hito 11 |
| Costo | Producto comercial (edición Community limitada); menos conocido por el equipo | — |

## Distribución, CAP y fallas (RF15)

| Módulo | Prioridad ante partición de red | Por qué |
|---|---|---|
| Comentarios (Cassandra) | **Disponibilidad** (AP, consistencia ajustable) | Durante un partido es mejor aceptar comentarios y mostrarlos 1-2 s tarde que rechazarlos |
| Sesiones (Redis) | Disponibilidad, con pérdida acotada (AOF 1 s) | Perder una sesión obliga a volver a iniciarla; no corrompe datos |
| Estado del partido (IRIS) | **Consistencia** (CP) | Un partido no puede estar "finalizado" en un nodo y "en juego" en otro |
| Equipos (MongoDB) | Consistencia en escritura (primario), lecturas eventuales | Cambian poco; leer una ficha con segundos de atraso no es grave |
| Estadísticas (InfluxDB) | Disponibilidad | Son mediciones continuas: un punto perdido se reemplaza con el siguiente |
| Grafo (Neo4j) | Consistencia en el líder, lecturas eventuales | Consultas de exploración, no transaccionales |

**Aislamiento de fallas medido**: en la prueba de falla controlada (Cassandra detenida), los endpoints de
MongoDB y Redis siguieron respondiendo 200 mientras los de comentarios respondían 503; al reiniciar
Cassandra la API se recuperó sola, sin reinicio. Ver `limitaciones_y_evidencia.md` y
`evidencia/prueba_de_falla_cassandra_*`.

**Lo que no se pudo demostrar en el laboratorio**: replicación real (todas las bases corren con un nodo),
caída de un nodo con la base siguiendo en servicio, latencia entre regiones. Es diseño, no medición.

## Mejora transversal analizada a partir de la evidencia (RF12)

**Evidencia**: en el Hito 12, con 60 usuarios, la API (un proceso de Python) llegó a ~90 % de un núcleo
mientras Cassandra tenía margen; la latencia medida dentro de la API subió de ~18 ms (sin carga) a
~140 ms de mediana. El cuello de botella era la integración (API), no la base.

**Mejoras aplicadas y medidas**: caché de la primera página en Redis (TTL 1 s) y varios procesos de la
API. Resultados en `hito-12-carga-optimizacion/docs/hipotesis_y_optimizacion.md`.

**Mejora transversal implementada a partir de la prueba de falla (Hito 13)**: corte rápido en el adaptador de
Cassandra. Con la base caída, los 503 tardaban hasta 8 s (reconexión bajo un lock, requests en fila); con el
corte rápido tardan 3 ms de mediana y la caída se reporta en 5 s en lugar de 30 s, a cambio de hasta 5 s más de
recuperación (`limitaciones_y_evidencia.md`).

**Mejora transversal propuesta (no implementada)**: aplicar el mismo patrón de *lectura caliente
cacheada* a otros endpoints de alto tráfico durante un partido (detalle del partido en IRIS, estadísticas
del último minuto en InfluxDB), con la tasa de aciertos visible en Grafana. Y para la observabilidad:
instrumentar Cassandra con el agente JMX, porque hoy la única visión de Cassandra es desde la API.

## Costo de operar seis modelos

Seis productos son seis formas de respaldar, actualizar, monitorear y diagnosticar. El equipo lo mitigó con:
un compose único con healthchecks (Hito 10), un adaptador por base con los mismos códigos de error
(503/504) y el mismo timeout (Hito 11), un diagnóstico de salud común (`/salud/dependencias`) y una sola capa
de monitoreo (este hito). Aun así, la consecuencia es real: más conocimiento necesario en el equipo de
guardia y más puntos de falla. Se justifica porque cada base atiende un patrón de acceso que las otras
resolverían peor (ver tablas anteriores); un producto que no cumpliera esa condición debería salir.
