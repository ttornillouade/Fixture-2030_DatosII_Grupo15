# Entorno de ejecución del Hito 12

La prueba usa **el mismo entorno del Hito 10**: las seis bases en Docker (`hito-10-api/compose.yaml`) y la
API FastAPI corriendo en la notebook. Este hito no agrega servicios: agrega un generador de carga, scripts
de medición y validación, y una optimización en la API.

## Entorno donde se midió

| Elemento | Valor observado |
|---|---|
| Equipo | PC de escritorio, Intel Core i5-9400F (6 núcleos, 6 hilos, 2,9 GHz), 16 GB de RAM |
| Sistema operativo | Windows 10 Pro 22H2 (10.0.19045) |
| Docker | Docker Desktop (motor 29.9.3, Compose v5.7.0), VM de WSL 2 con 6 CPU y 7,7 GB asignados |
| Python (API y generador) | 3.11.3 (el README del Hito 10 pide 3.12; con 3.11 funciona igual) |
| API | FastAPI 0.143.0 + uvicorn 0.54.0, `--host 127.0.0.1 --port 8000 --no-access-log` |
| Versiones de las imágenes | quedan registradas en cada `resumen.json` (`versiones`): imagen + digest de cada contenedor |

La notebook es a la vez generador, API y host de las bases: **compiten por los mismos 6 núcleos**. Por eso
cada corrida registra la CPU de cada componente por separado (ver `docs/linea_base.md`).

## Diferencias respecto del Hito 10 (Windows)

El compose del Hito 10 se escribió en macOS y monta `~/docker/data/<base>`. En Windows, MongoDB,
Cassandra e IRIS no funcionan bien sobre carpetas NTFS montadas, así que se agregó un **override** que
reemplaza esos directorios por volúmenes de Docker, sin tocar el compose original:

```bash
cd hito-10-api
docker compose -f compose.yaml -f ../hito-12-carga-optimizacion/config/compose.volumenes-docker.yaml up -d --wait
```

El override también limita el heap de Cassandra a 1 GB (`MAX_HEAP_SIZE`), para que la base no tome la mitad
de la memoria de la VM (RNF9).

**IRIS en un volumen nuevo**: IRIS necesita que `/durable` pertenezca a su usuario (uid 51773). Solo la
primera vez:

```bash
docker run --rm -v hito-10-api_fixture2030-iris:/d busybox:1.36 chown 51773:51773 /d
docker restart fixture2030-iris
```

**Entorno virtual en Windows**: los scripts del Hito 10 usan `.venv/bin/python`; en Windows el venv crea
`.venv\Scripts`. Se resuelve con un enlace (junction), una sola vez por venv:

```bash
cmd //c "mklink /J .venv\\bin .venv\\Scripts"
```

En macOS o Linux nada de esto hace falta: se usa el compose del Hito 10 tal cual.

## Configuración y secretos

| Archivo | Contenido | Versionado |
|---|---|---|
| `hito-10-api/.env` | conexiones y credenciales de la API (Neo4j, IRIS, token de InfluxDB) | **No** |
| `config/escenario.json` | escenario de carga (VU, etapas, proporciones, think time) | Sí |
| `config/compose.volumenes-docker.yaml` | override de volúmenes para Windows | Sí |
| `config/api_<corrida>.log` | log de la API de cada corrida (insumo de `servidor.json`) | No |

Los scripts del Hito 12 no leen ni imprimen secretos: el generador habla solo con la API y la validación
se conecta a Cassandra y Redis, que en el laboratorio no tienen autenticación y escuchan solo en `127.0.0.1`.
