# Grupo 15 — Hito 11 — Evaluación de la conectividad del Fixture 2030

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

Procedimiento reproducible para evaluar, capa por capa, la conectividad de la API integrada del
Hito 10 (`hito-10-api/`) con sus seis productos: MongoDB, Neo4j, Cassandra, Redis, InfluxDB e IRIS.
Las pruebas corren **desde la notebook, el mismo entorno que la API**, con los mismos drivers y el
mismo `.env`. Todas son lecturas, pings o consultas constantes: no modifican datos.

## Documentación

| Apartado | Documento |
|---|---|
| Mapa de dependencias y variables | [docs/mapa_de_dependencias.md](docs/mapa_de_dependencias.md) |
| Topología, puertos publicados e internos, `localhost` en cada entorno | [docs/topologia_y_entornos.md](docs/topologia_y_entornos.md) |
| Capas de evaluación, estados y matriz | [docs/matriz_de_conectividad.md](docs/matriz_de_conectividad.md) |
| Comportamiento de la API ante fallas, hallazgos y fallas controladas | [docs/diagnostico_de_fallas.md](docs/diagnostico_de_fallas.md) |
| Liveness, diagnóstico por dependencia y propuesta de readiness | [docs/health_readiness.md](docs/health_readiness.md) |
| Evidencia (salidas redactadas, sin secretos) | [docs/evidencia/](docs/evidencia/) |

## Requisitos

- Las seis bases y sus datos del Hito 10: `bash ../hito-10-api/scripts/levantar_todo.sh`.
- El entorno virtual de la API (`../hito-10-api/.venv`), que tiene los drivers. Los scripts del Hito 11 lo usan.
- Docker, solo para las fallas controladas (`prueba_falla.sh`).
- Los CLI nativos (`mongosh`, `cypher-shell`, `cqlsh`, `redis-cli`, `influxdb3`, `iris`) son
  **opcionales**: si no están en la notebook, esa prueba es SKIP y la evaluación sigue con el driver.

## Configuración

| Archivo | Contenido | Versionado |
|---|---|---|
| `../hito-10-api/.env` | Conexiones de la API (hosts, puertos, contextos, credenciales) | No |
| `config/configuracion-ejemplo.env` | `ENV_API`, `API_URL`, `API_LOG`, `TIMEOUT_S`, URLs de los portales de Neo4j e IRIS | Sí (sin secretos) |
| `config/local.env` | Copia del ejemplo con valores propios del entorno, si hace falta cambiarlos | No |

Las variables de entorno tienen prioridad. Por ejemplo, `TIMEOUT_S=5 bash scripts/evaluar_conectividad.sh`.

## Orden de ejecución

Desde `hito-11-conectividad/`:

```bash
bash ../hito-10-api/scripts/preparar_datos_demo.sh
```

```bash
(cd ../hito-10-api && bash scripts/iniciar_api.sh) > docs/evidencia/api.log 2>&1 &
```

```bash
bash scripts/evaluar_conectividad.sh
```

```bash
bash scripts/prueba_falla.sh detener redis
```

```bash
bash scripts/prueba_falla.sh pausar neo4j
```

1. Deja la sesión de prueba de Redis y el partido P128 (datos del laboratorio).
2. Inicia la API con su salida en `docs/evidencia/api.log`, para correlacionar cada `requestId` con su
   línea de log. Ese archivo no se versiona.
3. Corre la evaluación completa: configuración y TCP → clientes → API. Escribe la matriz.
4. y 5. Fallas controladas: detener (la base rechaza la conexión) y pausar (acepta y no responde).
   También con `mongodb`, `cassandra`, `influxdb` o `iris`.

### Modos

```bash
bash scripts/evaluar_conectividad.sh --modo tcp
```

```bash
bash scripts/evaluar_conectividad.sh --modo clientes --producto cassandra,iris
```

```bash
bash scripts/evaluar_conectividad.sh --modo api --producto redis
```

`--modo` es `completo` (por defecto), `tcp`, `clientes` o `api`. `--producto` acepta una lista
separada por comas. Cada producto se evalúa por separado: una base caída no impide evaluar las demás
(RNF13).

**SKIP** significa "prueba no ejecutada por falta de herramienta o configuración", **no** "producto
caído". Al terminar, el script verifica que ningún valor secreto del `.env` aparezca en la evidencia.

## Estructura

```text
hito-11-conectividad/
├── config/configuracion-ejemplo.env   variables del diagnóstico (sin secretos)
├── scripts/
│   ├── evaluar_conectividad.sh   orquestador: modos, productos, evidencia, matriz, control de secretos
│   ├── prueba_tcp.py             configuración, resolución y TCP (y contrastes de la tabla 5.3)
│   ├── prueba_clientes.py        protocolo, autenticación, autorización, contexto y lectura por producto
│   ├── prueba_api.py             rutas del Hito 10 con status, duración, requestId y log
│   ├── prueba_falla.sh           detener o pausar una base, observar y recuperar
│   ├── resumen.py                matriz de conectividad a partir de los resultados
│   └── comun.py                  configuración, registro de resultados y redacción de secretos
└── docs/                         análisis y evidencia
```

## Cambios en la API del Hito 10

La evaluación encontró fallas que la consigna pide corregir (detalle en
[diagnostico_de_fallas.md](docs/diagnostico_de_fallas.md)):

- **504 `DEPENDENCY_TIMEOUT`** cuando una base acepta la conexión y no responde. **503** queda para
  cuando la rechaza.
- **Límite de 3 s en todas las bases.** MongoDB tardaba 8,6 s en fallar, y Neo4j e IRIS bloqueaban la
  request mientras la base estaba colgada.
- **`GET /salud`** (liveness) y **`GET /salud/dependencias`** (un ping por base, que también detecta
  una database de MongoDB mal escrita).

## Limitaciones

- Una sola notebook, un nodo por base y la red local de Docker: no se probó red real, firewall ni DNS
  externo. El *timeout* de red se mostró con una dirección sin ruta (`10.255.255.1`).
- El laboratorio no tiene autenticación en MongoDB, Cassandra ni Redis. Esas capas quedan en SKIP, y
  la autorización de Neo4j Community no tiene roles.
- Los CLI nativos no están instalados en la notebook (SKIP). Están dentro de los contenedores, que son
  otro origen.
- OK significa que esa prueba funcionó en ese momento. No mide rendimiento ni capacidad de carga.

## Coherencia con el TPO

Cada producto se evalúa con el contexto de su hito: `fixture2030.equipos` (Hito 4), el grafo de
jugadores y partidos (Hito 5), la partición `(partido_id, bucket_5m, shard)` de comentarios (Hito 6),
la sesión `fixture2030:session:s-demo-001` con TTL (Hito 7), la ventana temporal de
`estadisticas_equipo` (Hito 8) y `Fixture.Partido` (Hito 9). La cadena completa usa las rutas de la
API del Hito 10.
