# Conectividad, configuración y seguridad

## Levantar las bases

Desde `hito-10-api/`, con Docker Desktop y Python 3.12 (los cargadores de InfluxDB e IRIS usan el
entorno virtual de la API):

```bash
cp .env.example .env        # definir NEO4J_PASSWORD e IRIS_PASSWORD
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/levantar_todo.sh
```

El script ejecuta `docker compose up -d --wait` (espera a que las 6 bases estén sanas), carga lo que
falte en cada una y verifica la conectividad:

| Base | Qué carga `scripts/inicializar_datos.sh` (solo si falta) | Desde |
|---|---|---|
| MongoDB | Equipos y jugadores con su validación e índices | `hito-4-mongodb/scripts` |
| Neo4j | Grafo completo (`estructura.cypher` + `carga.cypher`) | `hito-5-neo4j/` |
| Cassandra | Esquema y carga de muestra (64 comentarios); la carga de volumen del Hito 6 es aparte | `Grupo_15_Hito_6_.../scripts` |
| Redis | Sesión de prueba `s-demo-001` (TTL de 30 minutos) | `scripts/preparar_datos_demo.sh` |
| InfluxDB | Token de administrador (si `INFLUX_TOKEN` está vacío, se crea y se guarda en `.env`), base `fixture2030_vivo` con retención de 14 días y 45.600 puntos de P001 a P004 con fecha del torneo | `scripts/influx/estadisticas.py`, `hito-5-neo4j/import/partidos.csv` |
| IRIS | Contraseña de `_SYSTEM`, clases del Hito 9 compiladas, 127 partidos con sus 508 eventos (con `RegistrarEvento` y un `%Save` por partido) y el partido de prueba P128 en `PROGRAMADO` | `hito-9-iris/scripts/Fixture`, `scripts/iris/partidos.py`, `hito-5-neo4j/import/` |

**Detener sin borrar datos:** `docker compose down`. Los datos quedan en `~/docker/data/{mongodb,redis,cassandra,neo4j,influxdb,iris}`, los mismos
directorios de cada hito.

## La API

Corre en la **notebook** (Python 3.12) y llega a las bases por `localhost`:

```bash
bash scripts/iniciar_api.sh        # http://localhost:8000/docs
```

Si la API corriera en un contenedor de la misma red, los hosts serían los nombres de los servicios
(`mongodb`, `redis`, `cassandra`, `neo4j`, `influxdb`, `iris`) en lugar de `localhost`.

| Base | Contenedor | Puerto | Variables |
|---|---|---|---|
| MongoDB | `fixture2030-mongodb` | 27017 | `MONGODB_URI`, `MONGODB_DATABASE` |
| Redis | `fixture2030-redis` | 6379 | `REDIS_URL` |
| Cassandra | `fixture2030-cassandra` | 9042 | `CASSANDRA_HOST`, `CASSANDRA_PORT`, `CASSANDRA_KEYSPACE` |
| Neo4j | `fixture2030-neo4j` | 7687 | `NEO4J_URI`, `NEO4J_USUARIO`, `NEO4J_PASSWORD` (la base se crea con ella) |
| InfluxDB | `fixture2030-influxdb` | 8181 | `INFLUX_URL`, `INFLUX_DATABASE`, `INFLUX_TOKEN` |
| IRIS | `fixture2030-iris` | 1972 | `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USUARIO`, `IRIS_PASSWORD` |
| Todas | — | — | `TIMEOUT_S` (3 s por operación) |

`bash scripts/verificar_conectividad.sh` prueba cada base con su cliente nativo (`mongosh`, `redis-cli`,
`cqlsh`, `cypher-shell`, la API HTTP de InfluxDB y el driver de IRIS).

## Seguridad

- **Secretos:** solo en `.env`, excluido por `.gitignore`. `.env.example` tiene las claves sin valores.
- **InfluxDB:** las consultas exigen el token; solo `/health` y `/ping` responden sin él, para el
  *healthcheck* (`--disable-authz health,ping`).
- **Respuestas:** los errores no incluyen URIs, consultas, credenciales ni trazas.
- **Logs:** una línea por request con método, ruta, fuente, estado, duración y `requestId`. No se
  registran query strings, cuerpos ni credenciales (`--no-access-log`).
- **Superficie:** el cliente no elige colección, tabla, keyspace, nodo ni comando: cada ruta tiene su
  consulta fija y parametrizada.
- **Red:** los puertos de las bases y de la API escuchan solo en `127.0.0.1`. Sin autenticación (fuera del alcance).
