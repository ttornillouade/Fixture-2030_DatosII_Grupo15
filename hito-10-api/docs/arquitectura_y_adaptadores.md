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

## Una base por funcionalidad

Cada módulo del TPO se expone sobre la base que lo implementó, como pide la consigna (RF2 a RF8):

| Funcionalidad | Hito | Base en la API |
|---|---|---|
| Equipos y jugadores | 4 | MongoDB |
| Relaciones | 5 | Neo4j (recorrido de partidos de un jugador) |
| Comentarios masivos | 6 | Cassandra |
| Sesiones | 7 | Redis |
| Estadísticas temporales | 8 | InfluxDB |
| Partido con estados y eventos | 9 | IRIS |

## Adaptadores

| Base | Módulo y driver | Contexto | Operación | Errores → 503 |
|---|---|---|---|---|
| MongoDB | `mongodb.py` · pymongo | database `fixture2030` | `equipos`/`jugadores`: `find` por `_id` y por `{equipoId, posicion}` ordenado por `dorsal`, paginado por clave | `PyMongoError` |
| Redis | `redis_sesiones.py` · redis | `fixture2030:session:{id}` (HASH, modelo del Hito 7) | `HGETALL` + `TTL`; `DEL` | `RedisError` |
| Cassandra | `cassandra.py` · cassandra-driver | keyspace `fixture2030_comments` | Sentencias preparadas sobre la partición `(partido_id, bucket_5m, shard)`: 8 lecturas asíncronas fusionadas; escritura en batch `LOGGED` en las 2 tablas | `NoHostAvailable`, timeouts, `Unavailable` |
| Neo4j | `neo4j_grafo.py` · neo4j | base por defecto, routing READ | `(Jugador)-[:PARTICIPA_EN]->(Partido)<-[:DISPUTA]-(rival)` parametrizado, `LIMIT 200` | `ServiceUnavailable`, `SessionExpired`, `AuthError` |
| InfluxDB | `influx.py` · httpx (API HTTP v3) | base `fixture2030_vivo` (retención 14 días), tabla `estadisticas_equipo` del Hito 8 | `POST /api/v3/query_sql` con parámetros (`$partido`, `$desde`, `$hasta`): ventana cruda o `date_bin` de 1 minuto (`avg` de posesión, `max` de pases y tiros) | errores de conexión, 401/403 y 5xx |
| IRIS | `iris.py` · intersystems-irispython | namespace `USER`, clases `Fixture.*` del Hito 9 | Detalle: proyección SQL de `Partido` y sus `Evento`, navegando `e.Jugador->Apellido`. Transición: `UPDATE ... WHERE Codigo = ? AND Estado = ?`, atómico; sin filas afectadas → 404 o 409 | `RuntimeError` al conectar; `OperationalError`, `InterfaceError` con la conexión abierta |

Los adaptadores se conectan **al primer uso**: la API arranca aunque una base esté caída, y ese
endpoint responde 503 mientras los demás siguen funcionando.

**IRIS y el modelo del Hito 9.** La API usa las clases del Hito 9 tal como quedaron después del
feedback (`Partido` con `Codigo`, `Estado` y sus eventos hijos), sin agregarles propiedades ni
métodos. Por eso el detalle devuelve el estado y los eventos, y la regla de transición
(`PROGRAMADO → EN_JUEGO → FINALIZADO`) está en el `UPDATE` condicionado del adaptador: un
`UPDATE` directo sobre la base, por fuera de la API, podría saltearla.

**Historial.** Entre el PR #7 y este cambio la API corrió sobre cuatro bases, con las estadísticas y
el partido en MongoDB (colección *time series* y documento con eventos embebidos). Se volvió a
InfluxDB e IRIS para cumplir RF7 y RF8 al pie de la letra.

## Mejoras propuestas (no implementadas)

| Mejora | Beneficio |
|---|---|
| Header `Idempotency-Key` con `SET NX` en Redis para los `POST` | Un reintento no duplica el comentario (hoy está documentado como no idempotente) |
| Caché en Redis de la ficha de equipo y de los partidos finalizados | Menos lecturas a MongoDB e IRIS; un partido finalizado no cambia, así que no hay riesgo de frescura |
| Validar en IRIS que el partido exista antes de comentar en Cassandra | Hoy Cassandra acepta comentarios de cualquier código de partido válido |
| Leer la agregación por minuto de `fixture2030_historico` (downsampling del Hito 8) | La agregación de una hora leería 120 filas en lugar de 7.200 puntos |
| Transición de estado como método de `Fixture.Partido` | La regla quedaría en la clase y valdría también fuera de la API |
| Compresión gzip de respuestas grandes | 15 minutos de puntos crudos ocupan unos 180 KB |
| Registrar eventos del partido por la API (`Partido.RegistrarEvento`) | Hoy se cargan desde los datos del Hito 5 |
| API en un contenedor dentro del compose | Un solo comando para bases y API |
