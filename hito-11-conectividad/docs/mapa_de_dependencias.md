# Mapa de dependencias

Dependencias de la API del Hito 10 (`hito-10-api/`). El **proceso que inicia la conexión** es siempre
la API (uvicorn, un proceso en la notebook) a través del driver de cada base; los scripts del Hito 11
corren en la misma notebook y usan los mismos drivers y el mismo `.env`.

Los seis productos del TPO están integrados: no hay productos `not_configured` en este entorno. El
estado observado de cada uno está en la [matriz de conectividad](matriz_de_conectividad.md).

| Producto | Módulo (hito) | Host desde la API | Puerto y protocolo | Contexto | Autenticación (sin valor) | Driver | Operación mínima | Endpoint de la API |
|---|---|---|---|---|---|---|---|---|
| MongoDB | Equipos y jugadores (4) | `localhost` (`MONGODB_URI`) | 27017, protocolo de MongoDB (OP_MSG) | database `fixture2030`, colecciones `equipos`, `jugadores` | ninguna en el laboratorio (URI sin usuario) | pymongo 4.18 | `ping` + `find_one({_id: "E010"})` | `GET /equipos/{codigo}`, `GET /jugadores` |
| Neo4j | Relaciones (5) | `localhost` (`NEO4J_URI`) | 7687, Bolt. El 7474 (HTTP, Browser) no lo usa la API | database `neo4j` | usuario `NEO4J_USUARIO` + `NEO4J_PASSWORD` | neo4j 6.4 | `RETURN 1` + `MATCH (j:Jugador {id: $id})` | `GET /jugadores/{codigo}/partidos` |
| Cassandra | Comentarios masivos (6) | `localhost` (`CASSANDRA_HOST`) | 9042, CQL nativo v5 | keyspace `fixture2030_comments`, tabla `comentarios_por_partido`, partición `(partido_id, bucket_5m, shard)` | ninguna (`AllowAllAuthenticator`) | cassandra-driver 3.30 | `SELECT release_version FROM system.local` + lectura de una partición con `LIMIT 1` | `GET` · `POST /partidos/{codigo}/comentarios` |
| Redis | Sesiones (7) | `localhost` (`REDIS_URL`) | 6379, RESP | db 0, claves `fixture2030:session:{id}` (HASH con TTL) | ninguna (sin `requirepass`) | redis-py 8.1 | `PING` + `EXISTS`/`TTL` de `s-demo-001` | `GET` · `DELETE /sesiones/{id}` |
| InfluxDB | Estadísticas temporales (8) | `localhost` (`INFLUX_URL`) | 8181, HTTP (API v3) | database `fixture2030_vivo`, tabla `estadisticas_equipo` | token de administrador `INFLUX_TOKEN` (Bearer) | httpx 0.28 | `GET /health` + `SELECT 1` + `count(*)` en una ventana de 2 s | `GET /partidos/{codigo}/estadisticas` |
| IRIS | Partido con estados (9) | `localhost` (`IRIS_HOST`) | 1972, Superserver. El 52773 (HTTP, Management Portal) no lo usa la API | namespace `USER`, clases `Fixture.*` | usuario `IRIS_USUARIO` + `IRIS_PASSWORD` | intersystems-irispython 5.4 | `SELECT 1` + `Fixture.Partido` por `Codigo` | `GET /partidos/{codigo}/detalle`, `PATCH /partidos/{codigo}/estado` |

**Estado esperado:** `up` para los seis, con los datos cargados por `hito-10-api/scripts/levantar_todo.sh`.
**Estado observado:** el de la última ejecución de `scripts/evaluar_conectividad.sh`
([`evidencia/matriz.md`](evidencia/matriz.md)).

## Puertos que el diagnóstico distingue

| Puerto | Qué es | Lo usa la API | Para qué lo prueba el Hito 11 |
|---|---|---|---|
| 7474 | Neo4j Browser (HTTP) | No | Mostrar que el portal responde aunque eso no prueba Bolt (RF10) |
| 52773 | IRIS Management Portal (HTTP) | No | Mostrar que el portal responde aunque eso no prueba el Superserver (RF14) |
| 7199 | JMX de Cassandra (interno) | No | Puerto interno no publicado: *connection refused* |
| 7000 | Gossip de Cassandra (interno) | No | En macOS lo ocupa AirPlay: conecta, pero no es Cassandra |
| 27018 | — | No | Puerto incorrecto: *connection refused* |

## Variables

Las conexiones se leen de `hito-10-api/.env` (no versionado; claves en `hito-10-api/.env.example`).
Las del diagnóstico, de `config/configuracion-ejemplo.env`. Ninguna salida muestra valores secretos:
las variables `*PASSWORD*`, `*TOKEN*` y `*SECRET*` se informan como `definida (oculta)` o `no definida`,
y una URI con usuario se muestra como `//***@host`.
