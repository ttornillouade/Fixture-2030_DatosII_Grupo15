# Grupo 15 — Hito 10 — API REST integrada del Fixture 2030

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

API en **FastAPI** que expone casos de uso del Fixture 2030 sobre las **seis bases del TPO: MongoDB,
Neo4j, Cassandra, Redis, InfluxDB e IRIS**. Cada endpoint consulta una sola base y respeta su modelo
de acceso.

> **Historial:** entre el PR #7 y esta versión la API corrió sobre cuatro bases, con las estadísticas
> (RF7) y el partido (RF8) en MongoDB. Se volvió a InfluxDB e IRIS para cumplir esos requisitos al pie
> de la letra. Ver [arquitectura](docs/arquitectura_y_adaptadores.md#una-base-por-funcionalidad).

## Endpoints

| Método y ruta | Base | Requisito |
|---|---|---|
| `GET /equipos/{codigo}` | MongoDB | RF3: ficha de un equipo |
| `GET /jugadores?equipoCodigo&posicion&limit&cursor` | MongoDB | RF3: plantel paginado por dorsal |
| `GET /jugadores/{codigo}/partidos` | Neo4j | RF4: partidos que jugó y contra quién (Cypher parametrizado) |
| `GET` · `POST /partidos/{codigo}/comentarios` | Cassandra | RF5: feed por partición (ventana de 5 min) y publicación |
| `GET` · `DELETE /sesiones/{id}` | Redis | RF6: sesión vigente, expirada o invalidada |
| `GET /partidos/{codigo}/estadisticas?desde&hasta&agregacion` | InfluxDB | RF7: ventana temporal, cruda o por minuto (SQL parametrizado) |
| `GET /partidos/{codigo}/detalle` | IRIS | RF8: entidad compleja, el partido con sus eventos (clases del Hito 9) |
| `PATCH /partidos/{codigo}/estado` | IRIS | RF8 y 5.10: transición validada (`PROGRAMADO → EN_JUEGO → FINALIZADO`) |

Errores: 400 validación, 404 inexistente, 409 transición ilegal, 503 base no disponible (timeout 3 s),
siempre como `{code, message, requestId}`.

## Documentación

| Apartado | Documento |
|---|---|
| Casos de uso | [docs/casos_de_uso.md](docs/casos_de_uso.md) |
| Arquitectura, adaptadores y mejoras propuestas | [docs/arquitectura_y_adaptadores.md](docs/arquitectura_y_adaptadores.md) |
| Contratos, validación, errores e idempotencia | [docs/contratos_y_errores.md](docs/contratos_y_errores.md) |
| Conectividad, configuración y seguridad | [docs/conectividad_y_configuracion.md](docs/conectividad_y_configuracion.md) |
| Pruebas, evidencia, rendimiento y coherencia con el TPO | [docs/pruebas_y_evidencia.md](docs/pruebas_y_evidencia.md) |
| Contrato OpenAPI | [openapi/openapi.yaml](openapi/openapi.yaml) |

## Estructura

```text
hito-10-api/
├── compose.yaml           las 6 bases, con healthchecks
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
│   ├── levantar_todo.sh   bases + carga de datos + verificación
│   ├── inicializar_datos.sh   lo que falte en cada base (idempotente)
│   ├── influx/            estadísticas de P001-P004 (CSV del Hito 5)
│   ├── iris/              partidos y eventos con las clases del Hito 9
│   ├── preparar_datos_demo.sh
│   ├── verificar_conectividad.sh
│   ├── iniciar_api.sh
│   ├── ejecutar_pruebas.sh
│   └── exportar_openapi.py
└── docs/                  análisis y evidencia
```

## Cómo correrla

Requisitos: Docker Desktop y Python 3.12. Desde `hito-10-api/`:

```bash
cp .env.example .env                                   # definir NEO4J_PASSWORD e IRIS_PASSWORD
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/levantar_todo.sh                          # bases + datos
bash scripts/iniciar_api.sh                            # http://localhost:8000/docs
```

Si `INFLUX_TOKEN` queda vacío, `levantar_todo.sh` crea el token de administrador de InfluxDB y lo
guarda en `.env`. Si InfluxDB ya tiene uno (por ejemplo, el del Hito 8), hay que copiarlo en `.env`.

En otra terminal, con la API corriendo:

```bash
bash scripts/ejecutar_pruebas.sh        # requiere Node (npx) para la CLI de Bruno
```

La colección también se abre en la app de Bruno: *Open Collection* → carpeta `bruno/` → entorno `local`.
Antes de repetirla, ejecutar `scripts/preparar_datos_demo.sh` (P128 en `PROGRAMADO` y sesión `s-demo-001`).

## Límites conocidos

- Cassandra arranca con una carga de muestra; la carga de volumen (1,1 M de comentarios) es la del Hito 6.
- Las estadísticas tienen fecha del torneo (2030): la retención de 14 días empezará a borrarlas recién
  después de esa fecha.
- La carga de IRIS vacía las clases `Fixture.*` antes de cargar, igual que la demo del Hito 9: correr
  la demo después borra los partidos de la API (se recuperan con `scripts/inicializar_datos.sh`).
- Sin autenticación: la API escucha solo en `127.0.0.1`.
