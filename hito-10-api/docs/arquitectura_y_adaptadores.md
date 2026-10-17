# Arquitectura y adaptadores

```text
Cliente (Bruno, Swagger UI, curl)
  └─ app/rutas/        Router: método, ruta, validación de path/query/body (Pydantic), fuente para el log
      └─ app/servicios.py   Caso de uso: reglas (ventanas, buckets, cursores)
          └─ app/adaptadores/   Un módulo por base: conexión, contexto, consulta, conversión y errores
              └─ driver nativo → base NoSQL
```

- `app/main.py`: crea la app, registra rutas, `requestId`, log y traducción de errores.
- `app/errores.py`: `Validacion` (400), `NoEncontrado` (404), `Conflicto` (409), `DependenciaNoDisponible` (503).
- `app/esquemas.py`: DTOs de entrada y salida (el contrato, no los documentos de cada base).
- `app/config.py`: configuración por variables de entorno (`.env`, fuera del repositorio).

## Desvío de RF7 y RF8: cuatro bases en lugar de seis

La consigna pide un endpoint de **InfluxDB (RF7)** y uno de **IRIS (RF8)**. El grupo decidió simplificar
la arquitectura del TPO a **MongoDB, Redis, Cassandra y Neo4j**, y cubrir con MongoDB las dos
funcionalidades. Lo que piden RF7 y RF8 se mantiene:

| Requisito | Qué pide | Cómo se cumple sin el motor original |
|---|---|---|
| RF7 | Estadísticas temporales, acotando intervalo y agregación | Colección **time series** de MongoDB (`timeField`, `metaField` con partido y equipo, índice `{meta, ts}`, retención automática de 14 días con `expireAfterSeconds`). El endpoint valida la ventana y agrega por minuto con `$dateTrunc` |
| RF8 (y 5.10) | Entidad compleja; validar transiciones; distinguir inexistente, transición inválida y dependencia caída | Documento `partido` con sus **eventos embebidos** (relación padre-hijo documental). La transición es un `update` **condicionado al estado de origen**, atómico en el documento: inexistente → 404, transición inválida → 409, base caída → 503 |

**Por qué:** seis motores son mucha infraestructura para el volumen del laboratorio, y las dos
funcionalidades encajan en el modelo documental sin perder lo que piden los requisitos. Una base
menos que operar por cada módulo también reduce los puntos de falla de la API.

**Lo que se resigna:** de InfluxDB, el formato *line protocol*; de IRIS, la herencia de clases y la
proyección SQL. Ninguno lo usaba la API. Además, MongoDB no impide modificar un partido con un
`update` directo sobre la base: la regla depende de que la API sea la única interfaz de escritura.

**Trazabilidad:** la versión de la API con seis bases (InfluxDB e IRIS incluidos) está en el historial
del repositorio, en el commit `d64d3e8`. Las carpetas `hito-8-influxdb/` e `hito-9-iris/` se conservan.

| Funcionalidad | Hito | Base en la API |
|---|---|---|
| Equipos y jugadores | 4 | MongoDB |
| Relaciones | 5 | Neo4j (recorrido de partidos de un jugador) |
| Comentarios masivos | 6 | Cassandra |
| Sesiones | 7 | Redis |
| Estadísticas temporales | 8 | MongoDB *time series* |
| Partido con estados y eventos | 9 | MongoDB `partidos` |

## Adaptadores

| Base | Módulo y driver | Contexto | Operación | Errores → 503 |
|---|---|---|---|---|
| MongoDB | `mongodb.py` · pymongo | database `fixture2030` | `equipos`/`jugadores`: `find` por `_id` y por `{equipoId, posicion}` ordenado por `dorsal`, paginado por clave. `partidos`: `aggregate` con `$size` de eventos; `update_one` condicionado al estado. `estadisticas`: `find` por `{meta.partidoId, ts}` o `$group` por `$dateTrunc` | `PyMongoError` |
| Redis | `redis_sesiones.py` · redis | `fixture2030:session:{id}` (HASH, modelo del Hito 7) | `HGETALL` + `TTL`; `DEL` | `RedisError` |
| Cassandra | `cassandra.py` · cassandra-driver | keyspace `fixture2030_comments` | Sentencias preparadas sobre la partición `(partido_id, bucket_5m, shard)`: 8 lecturas asíncronas fusionadas; escritura en batch `LOGGED` en las 2 tablas | `NoHostAvailable`, timeouts, `Unavailable` |
| Neo4j | `neo4j_grafo.py` · neo4j | base por defecto, routing READ | `(Jugador)-[:PARTICIPA_EN]->(Partido)<-[:DISPUTA]-(rival)` parametrizado, `LIMIT 200` | `ServiceUnavailable`, `SessionExpired`, `AuthError` |

Los adaptadores se conectan **al primer uso**: la API arranca aunque una base esté caída, y ese
endpoint responde 503 mientras los demás siguen funcionando.

## Mejoras propuestas (no implementadas)

| Mejora | Beneficio |
|---|---|
| Header `Idempotency-Key` con `SET NX` en Redis para los `POST` | Un reintento no duplica el comentario (hoy está documentado como no idempotente) |
| Caché en Redis de la ficha de equipo y de los partidos finalizados | Menos lecturas a MongoDB; un partido finalizado no cambia, así que no hay riesgo de frescura |
| Validar en MongoDB que el partido exista antes de comentar en Cassandra | Hoy Cassandra acepta comentarios de cualquier código de partido válido |
| Resúmenes por minuto precalculados (`$merge`) al finalizar el partido | La agregación de una hora leería 120 documentos en lugar de 7.200 puntos |
| Compresión gzip de respuestas grandes | 15 minutos de puntos crudos ocupan unos 180 KB |
| Registrar eventos del partido por la API | Hoy se cargan desde los datos del Hito 5 |
| API en un contenedor dentro del compose | Un solo comando para bases y API |
