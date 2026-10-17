# Grupo 15 — Hito 10 — API REST integrada del Fixture 2030

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

API en **FastAPI** que expone casos de uso del Fixture 2030 sobre **cuatro bases: MongoDB, Redis,
Cassandra y Neo4j**. Cada endpoint consulta una sola base y respeta su modelo de acceso.

> Las estadísticas temporales (RF7) y el partido como entidad compleja (RF8) se resuelven con
> MongoDB. La decisión y cómo se cumple lo que piden esos requisitos están en
> [arquitectura](docs/arquitectura_y_adaptadores.md#desvío-de-rf7-y-rf8-cuatro-bases-en-lugar-de-seis).

## Endpoints

| Método y ruta | Base | Requisito |
|---|---|---|
| `GET /equipos/{codigo}` | MongoDB | RF3: ficha de un equipo |
| `GET /jugadores?equipoCodigo&posicion&limit&cursor` | MongoDB | RF3: plantel paginado por dorsal |
| `GET /jugadores/{codigo}/partidos` | Neo4j | RF4: partidos que jugó y contra quién (Cypher parametrizado) |
| `GET` · `POST /partidos/{codigo}/comentarios` | Cassandra | RF5: feed por partición (ventana de 5 min) y publicación |
| `GET` · `DELETE /sesiones/{id}` | Redis | RF6: sesión vigente, expirada o invalidada |
| `GET /partidos/{codigo}/estadisticas?desde&hasta&agregacion` | MongoDB time series | RF7: ventana temporal, cruda o por minuto |
| `GET /partidos/{codigo}/detalle` | MongoDB | RF8: entidad compleja |
| `PATCH /partidos/{codigo}/estado` | MongoDB | RF8 y 5.10: transición validada (`PROGRAMADO → EN_JUEGO → FINALIZADO`) |

Errores: 400 validación, 404 inexistente, 409 transición ilegal, 503 base no disponible (timeout 3 s),
siempre como `{code, message, requestId}`.

## Documentación

| Apartado | Documento |
|---|---|
| Casos de uso | [docs/casos_de_uso.md](docs/casos_de_uso.md) |
| Arquitectura, adaptadores, desvío de RF7/RF8 y mejoras propuestas | [docs/arquitectura_y_adaptadores.md](docs/arquitectura_y_adaptadores.md) |
| Contratos, validación, errores e idempotencia | [docs/contratos_y_errores.md](docs/contratos_y_errores.md) |
| Conectividad, configuración y seguridad | [docs/conectividad_y_configuracion.md](docs/conectividad_y_configuracion.md) |
| Pruebas, evidencia, rendimiento y coherencia con el TPO | [docs/pruebas_y_evidencia.md](docs/pruebas_y_evidencia.md) |
| Contrato OpenAPI | [openapi/openapi.yaml](openapi/openapi.yaml) |

## Estructura

```text
hito-10-api/
├── compose.yaml           las 4 bases, con healthchecks
├── app/
│   ├── main.py            app, requestId, log y traducción de errores
│   ├── rutas/             HTTP: rutas, parámetros y validación
│   ├── servicios.py       casos de uso
│   ├── adaptadores/       mongodb, redis_sesiones, cassandra, neo4j_grafo
│   ├── esquemas.py        DTOs de request y response
│   ├── errores.py         errores de la API
│   └── config.py          configuración desde variables de entorno
├── datos/                 sedes, partidos y eventos (CSV del Hito 5)
├── openapi/openapi.yaml   contrato generado desde el código
├── bruno/                 colección de pruebas (Bruno), entorno local
├── scripts/
│   ├── levantar_todo.sh   bases + carga de datos + verificación
│   ├── inicializar_datos.sh
│   ├── cargar_datos.sh    partidos, eventos y estadísticas en MongoDB
│   ├── mongo/
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
cp .env.example .env                                   # definir NEO4J_PASSWORD
bash scripts/levantar_todo.sh                          # bases + datos
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/iniciar_api.sh                            # http://localhost:8000/docs
```

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
- Sin autenticación: la API escucha solo en `127.0.0.1`.
