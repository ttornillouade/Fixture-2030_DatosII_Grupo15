# Conectividad, configuración y seguridad

## Levantar las bases

Desde `hito-10-api/`, con Docker Desktop:

```bash
cp .env.example .env        # definir NEO4J_PASSWORD
bash scripts/levantar_todo.sh
```

El script ejecuta `docker compose up -d --wait` (espera a que las 4 bases estén sanas), carga lo que
falte en cada una y verifica la conectividad:

| Base | Qué carga `scripts/inicializar_datos.sh` (solo si falta) | Desde |
|---|---|---|
| MongoDB | Equipos y jugadores con su validación e índices; partidos con eventos y estadísticas | `hito-4-mongodb/scripts`, `datos/`, `scripts/mongo/` |
| Neo4j | Grafo completo (`estructura.cypher` + `carga.cypher`) | `hito-5-neo4j/` |
| Cassandra | Esquema y carga de muestra (64 comentarios); la carga de volumen del Hito 6 es aparte | `Grupo_15_Hito_6_.../scripts` |
| Redis | Sesión de prueba `s-demo-001` (TTL de 30 minutos) | `scripts/preparar_datos_demo.sh` |

**Detener sin borrar datos:** `docker compose down`. Los datos quedan en `~/docker/data/{mongodb,redis,cassandra,neo4j}`.

## La API

Corre en la **notebook** (Python 3.12) y llega a las bases por `localhost`:

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/iniciar_api.sh        # http://localhost:8000/docs
```

Si la API corriera en un contenedor de la misma red, los hosts serían los nombres de los servicios
(`mongodb`, `redis`, `cassandra`, `neo4j`) en lugar de `localhost`.

| Base | Contenedor | Puerto | Variables |
|---|---|---|---|
| MongoDB | `fixture2030-mongodb` | 27017 | `MONGODB_URI`, `MONGODB_DATABASE` |
| Redis | `fixture2030-redis` | 6379 | `REDIS_URL` |
| Cassandra | `fixture2030-cassandra` | 9042 | `CASSANDRA_HOST`, `CASSANDRA_PORT`, `CASSANDRA_KEYSPACE` |
| Neo4j | `fixture2030-neo4j` | 7687 | `NEO4J_URI`, `NEO4J_USUARIO`, `NEO4J_PASSWORD` (la base se crea con ella) |
| Todas | — | — | `TIMEOUT_S` (3 s por operación) |

`bash scripts/verificar_conectividad.sh` prueba cada base con su cliente nativo (`mongosh`, `redis-cli`,
`cqlsh`, `cypher-shell`).

## Seguridad

- **Secretos:** solo en `.env`, excluido por `.gitignore`. `.env.example` tiene las claves sin valores.
- **Respuestas:** los errores no incluyen URIs, consultas, credenciales ni trazas.
- **Logs:** una línea por request con método, ruta, fuente, estado, duración y `requestId`. No se
  registran query strings, cuerpos ni credenciales (`--no-access-log`).
- **Superficie:** el cliente no elige colección, tabla, keyspace, nodo ni comando: cada ruta tiene su
  consulta fija y parametrizada.
- **Red:** los puertos de las bases y de la API escuchan solo en `127.0.0.1`. Sin autenticación (fuera del alcance).
