# Conectividad, configuración y seguridad

## Dónde corre cada componente

La API corre en la **notebook** (Python 3.12) y las bases en **Docker**, publicadas en `localhost`.
Si la API corriera en un contenedor, los hosts cambiarían por los nombres de los servicios en una
red de Docker compartida (por ejemplo `mongodb://fixture2030-mongodb:27017`); los puertos internos
son los mismos.

| Base | Contenedor (proyecto) | Puerto local | Variables |
|---|---|---|---|
| MongoDB | `fixture2030-mongodb` (`hito-4-mongodb/`) | 27017 | `MONGODB_URI`, `MONGODB_DATABASE` |
| Neo4j | `fixture2030-neo4j` (Hito 5) | 7687 | `NEO4J_URI`, `NEO4J_USUARIO`, `NEO4J_PASSWORD` |
| Cassandra | `fixture2030-cassandra` (Hito 6) | 9042 | `CASSANDRA_HOST`, `CASSANDRA_PORT`, `CASSANDRA_KEYSPACE` |
| Redis | `fixture2030-redis` (Hito 7) | 6379 | `REDIS_URL` |
| InfluxDB | `fixture2030-influxdb` (`hito-8-influxdb/`) | 8181 | `INFLUX_URL`, `INFLUX_DATABASE`, `INFLUX_TOKEN` |
| IRIS | `fixture2030-iris` (`hito-9-iris/`) | 1972 | `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USUARIO`, `IRIS_PASSWORD` |
| Todas | — | — | `TIMEOUT_S` (3 s por operación) |

## Procedimiento

1. Levantar cada base con el `docker compose up -d` de su hito.
2. `cp .env.example .env` y completar los tokens y contraseñas locales.
3. `bash scripts/preparar_datos_demo.sh`: contraseña de `_SYSTEM` en IRIS y partido P003 en `PROGRAMADO`.
4. `bash scripts/verificar_conectividad.sh`: prueba cada base con su cliente nativo (`mongosh`,
   `cypher-shell`, `cqlsh`, `redis-cli`, `/health` de InfluxDB, terminal de IRIS).
5. `bash scripts/iniciar_api.sh`.

**Detener sin borrar datos:** Ctrl+C en la API y `docker compose down` en cada hito; los datos
quedan en `~/docker/data/` o en los volúmenes de Docker.

## Seguridad

- **Secretos:** solo en `.env`, excluido por `.gitignore`. `.env.example` tiene las claves sin valores.
- **Respuestas:** los errores no incluyen URIs, consultas, credenciales ni trazas.
- **Logs:** una línea por request con método, ruta, fuente, estado, duración y `requestId`. No se
  registran query strings, cuerpos ni credenciales. La API se inicia con `--no-access-log` para que
  uvicorn tampoco los registre.
- **Superficie:** el cliente no elige colección, tabla, keyspace, nodo ni comando: cada ruta tiene
  su consulta fija y parametrizada.
- La API escucha solo en `127.0.0.1` y no implementa autenticación (fuera del alcance del hito).
