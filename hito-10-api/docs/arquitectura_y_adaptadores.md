# Arquitectura y adaptadores

```text
Cliente (Bruno, Swagger UI, curl)
  └─ app/rutas/        Router: método, ruta, validación de path/query/body (Pydantic), fuente para el log
      └─ app/servicios.py   Caso de uso: reglas (ventanas, buckets, cursores) y orquestación
          └─ app/adaptadores/   Un módulo por base: conexión, contexto, consulta, conversión y errores
              └─ driver nativo → base NoSQL
```

- `app/main.py`: crea la app, registra rutas, `requestId`, log y traducción de errores.
- `app/errores.py`: `Validacion` (400), `NoEncontrado` (404), `Conflicto` (409), `DependenciaNoDisponible` (503).
- `app/esquemas.py`: DTOs de entrada y salida; son el contrato, no los documentos de cada base.
- `app/config.py`: configuración por variables de entorno (`.env`, fuera del repositorio).

Ninguna ruta conoce un driver: los detalles de cada producto quedan en su adaptador (RNF5).

## Adaptadores

| Base | Módulo y driver | Contexto | Operación | Conversión | Errores → 503 |
|---|---|---|---|---|---|
| MongoDB (Hito 4) | `mongodb.py` · pymongo | database `fixture2030` | `find_one` por `_id`; `find` por `{equipoId, posicion}` ordenado por `dorsal` (índice `equipo_posicion_dorsal`), paginado por clave | Proyección de los campos del contrato, sin `_id` interno ni `updatedAt` | `PyMongoError` (incluye timeout de selección de servidor) |
| Neo4j (Hito 5) | `neo4j_grafo.py` · neo4j | base por defecto, routing READ | Cypher parametrizado `(Evento)-[:OCURRE_EN]->(Partido {id: $codigo})`, `LIMIT 200` | Registros a `{tipo, minuto, jugadorCodigo}` | `ServiceUnavailable`, `SessionExpired`, `AuthError` |
| Cassandra (Hito 6) | `cassandra.py` · cassandra-driver | keyspace `fixture2030_comments` | Sentencias preparadas sobre la partición `(partido_id, bucket_5m, shard)`: 8 lecturas asíncronas fusionadas por fecha; escritura en batch `LOGGED` en las 2 tablas | Filas a comentarios; cursor opaco `(creado_en, comentario_id)` | `NoHostAvailable`, `OperationTimedOut`, `Read/WriteTimeout`, `Unavailable` |
| Redis (Hito 7) | `redis_sesiones.py` · redis | `fixture2030:session:{id}` (HASH) | `HGETALL` + `TTL`; `HSET` + `EXPIRE` en transacción; `DEL` | Solo usuario, estado, locale, alta y TTL | `RedisError` |
| InfluxDB (Hito 8) | `influx.py` · httpx | database `fixture2030_vivo`, token | `POST /api/v3/query_sql` con parámetros `$partido`, `$desde`, `$hasta` | Puntos con hora UTC; por minuto: `avg` de posesión, `max` de pases y tiros (acumulados) | Error de red, 401/403 y 5xx |
| IRIS (Hito 9) | `iris.py` · intersystems-irispython | namespace `USER`, clase `Fixture.Partido` | Lectura por proyección SQL; escritura con `Fixture.Partido.CambiarEstado` (Native API) | Detalle acotado del partido | Error de conexión |

Los adaptadores se conectan **al primer uso**: la API arranca aunque una base esté caída, y ese
endpoint responde 503 mientras los demás siguen funcionando. Cassandra e IRIS descartan la conexión
ante un error y se reconectan en la request siguiente; los demás drivers lo hacen solos.

**Por qué IRIS combina dos interfaces:** la lectura es una consulta tabular acotada (proyección SQL);
la escritura pasa por la clase para no saltear `Iniciar`/`Finalizar` (Clase 11: "no saltar
validaciones de dominio").
