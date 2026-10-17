# Grupo 15 — Hito 10 — API REST integrada del Fixture 2030

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

API en **FastAPI** que expone casos de uso del Fixture 2030 sobre las seis bases del TPO.
Cada endpoint consulta **una sola base** y respeta su modelo de acceso.

## Endpoints

| Método y ruta | Base (hito) | Caso de uso |
|---|---|---|
| `GET /equipos/{codigo}` | MongoDB (4) | Ficha de un equipo |
| `GET /jugadores?equipoCodigo&posicion&limit&cursor` | MongoDB (4) | Plantel por posición, paginado por dorsal |
| `GET /partidos/{codigo}/eventos` | Neo4j (5) | Hechos del partido en el grafo |
| `GET /partidos/{codigo}/comentarios?bucket&limit&cursor` | Cassandra (6) | Feed de comentarios de una ventana de 5 minutos |
| `POST /partidos/{codigo}/comentarios` | Cassandra (6) | Publicar un comentario |
| `POST /sesiones` · `GET` · `DELETE /sesiones/{id}` | Redis (7) | Crear, validar e invalidar una sesión |
| `GET /partidos/{codigo}/estadisticas?desde&hasta&agregacion` | InfluxDB (8) | Evolución del partido en una ventana |
| `GET /partidos/{codigo}/detalle` | IRIS (9) | Estado del partido |
| `PATCH /partidos/{codigo}/estado` | IRIS (9) | Iniciar o finalizar el partido (transición validada) |

Errores: 400 validación, 404 inexistente, 409 transición ilegal, 503 base no disponible (timeout 3 s),
siempre como `{code, message, requestId}`.

## Documentación

| Apartado | Documento |
|---|---|
| Casos de uso | [docs/casos_de_uso.md](docs/casos_de_uso.md) |
| Arquitectura y adaptadores | [docs/arquitectura_y_adaptadores.md](docs/arquitectura_y_adaptadores.md) |
| Contratos, validación, errores e idempotencia | [docs/contratos_y_errores.md](docs/contratos_y_errores.md) |
| Conectividad, configuración y seguridad | [docs/conectividad_y_configuracion.md](docs/conectividad_y_configuracion.md) |
| Pruebas, evidencia, rendimiento y coherencia con el TPO | [docs/pruebas_y_evidencia.md](docs/pruebas_y_evidencia.md) |
| Contrato OpenAPI | [openapi/openapi.yaml](openapi/openapi.yaml) |

## Estructura

```text
hito-10-api/
├── app/
│   ├── main.py            app, requestId, log y traducción de errores
│   ├── rutas/             HTTP: rutas, parámetros y validación
│   ├── servicios.py       casos de uso
│   ├── adaptadores/       mongodb, neo4j_grafo, cassandra, redis_sesiones, influx, iris
│   ├── esquemas.py        DTOs de request y response
│   ├── errores.py         errores de la API
│   └── config.py          configuración desde variables de entorno
├── openapi/openapi.yaml   contrato generado desde el código
├── bruno/                 colección de pruebas (Bruno), entorno local
├── scripts/
│   ├── iniciar_api.sh
│   ├── verificar_conectividad.sh
│   ├── preparar_datos_demo.sh
│   ├── ejecutar_pruebas.sh
│   └── exportar_openapi.py
└── docs/                  análisis y evidencia
```

## Cómo correrla

Requisitos: Python 3.12, Docker y las bases de los hitos 4 a 9 levantadas
(ver [conectividad](docs/conectividad_y_configuracion.md)). Desde `hito-10-api/`:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                    # completar tokens y contraseñas locales
bash scripts/verificar_conectividad.sh
bash scripts/preparar_datos_demo.sh
bash scripts/iniciar_api.sh             # http://localhost:8000/docs
```

En otra terminal, con la API corriendo:

```bash
bash scripts/ejecutar_pruebas.sh        # requiere Node (npx) para la CLI de Bruno
```

La colección también se abre en la app de Bruno: *Open Collection* → carpeta `bruno/` → entorno `local`.
Antes de repetir la carpeta `06-iris`, ejecutar `scripts/preparar_datos_demo.sh` (deja P003 en `PROGRAMADO`).

## Límites conocidos

- La API no combina bases en una misma respuesta.
- `fixture2030_vivo` (InfluxDB) tiene retención de 14 días: los datos de prueba del 2026-10-04
  vencen alrededor del 2026-10-18.
- IRIS identifica jugadores como `E001J09`; MongoDB y Neo4j, como `E001-J09`.
- Sin autenticación: la API escucha solo en `127.0.0.1`.
