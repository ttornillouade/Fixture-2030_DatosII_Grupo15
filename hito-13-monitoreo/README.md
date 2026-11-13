# Grupo 15 — Hito 13 — Monitoreo y defensa final del Fixture 2030

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

Capa de observabilidad de la plataforma con **Prometheus y Grafana** sobre la API integrada (Hito 10) y las
seis bases (MongoDB, Neo4j, Cassandra, Redis, InfluxDB, IRIS), una prueba de falla controlada con
evidencia, y el material de la defensa ante la FIFA.

## Qué se monitorea

| Fuente de métricas | Tipo | Componentes |
|---|---|---|
| `GET /metrics` de la API (`hito-10-api/app/metricas.py`) | **aplicación** (medido por la API) | requests, latencia y errores por ruta y por base; estado de cada base según su driver; aciertos de la caché |
| `redis_exporter`, `mongodb_exporter` | **infraestructura** (exporter) | Redis, MongoDB |
| `blackbox_exporter` (TCP y HTTP) | **sonda sintética** | las 6 bases y la API |

Cassandra, Neo4j, InfluxDB e IRIS no tienen exporter propio en el laboratorio: se observan por sonda TCP,
por el ping de la API y por las métricas de sus endpoints. Detalle y motivos en
[docs/inventario_de_componentes.md](docs/inventario_de_componentes.md).

## Documentación

| Tema | Documento |
|---|---|
| Inventario de componentes y qué se mide de cada uno | [docs/inventario_de_componentes.md](docs/inventario_de_componentes.md) |
| Configuración de Prometheus, targets, UP/DOWN, consultas PromQL | [docs/metricas_y_consultas.md](docs/metricas_y_consultas.md) |
| Alertas y umbrales | [docs/alertas_y_umbral.md](docs/alertas_y_umbral.md) |
| Decisiones de arquitectura (base de la defensa) | [docs/decisiones_de_arquitectura.md](docs/decisiones_de_arquitectura.md) |
| Limitaciones y evidencia (prueba de falla) | [docs/limitaciones_y_evidencia.md](docs/limitaciones_y_evidencia.md) |
| Defensa: síntesis | [docs/defensa_final.md](docs/defensa_final.md) |
| Defensa: guion de 20 minutos, demo y presentación | [defensa/](defensa/) |
| Dashboard | [grafana/README.md](grafana/README.md) |

## Estructura

```text
hito-13-monitoreo/
├── docker-compose.yml        Prometheus, Grafana, redis/mongodb/blackbox exporters (red del Hito 10)
├── prometheus.yml            scraping cada 5 s, jobs y etiquetas
├── prometheus/reglas-o-alertas.yml   reglas de registro y 5 alertas
├── blackbox/blackbox.yml     módulos de sonda TCP y HTTP
├── grafana/                  provisioning, dashboard (JSON generado por generar_dashboard.py)
├── scripts/
│   ├── iniciar_monitoreo.sh  levanta todo y verifica los targets
│   ├── verificar_targets.py  estado de cada target y de cada base (--guardar deja evidencia)
│   ├── ejecutar_prueba_controlada.py   falla controlada con evidencia de Prometheus y Grafana
│   └── limpiar_entorno.sh    baja el monitoreo (no toca las bases)
├── docs/                     análisis
├── evidencia/                targets, prueba de falla, capturas del dashboard
└── defensa/                  guion, demo y presentación
```

## Requisitos

- Las seis bases del Hito 10 corriendo (crean la red `hito-10-api_default`).
- La API del Hito 10 con `prometheus-client` (`pip install -r hito-10-api/requirements.txt`).
- Python 3.11+ para los scripts de este hito (`requirements.txt`: httpx y matplotlib).

## Cómo correrlo

```bash
cd hito-13-monitoreo && cp .env.example .env
```

```bash
cd hito-10-api && CACHE_COMENTARIOS_TTL_MS=1000 bash scripts/iniciar_api.sh
```

```bash
cd hito-13-monitoreo && python -m venv .venv && .venv/bin/pip install -r requirements.txt && bash scripts/iniciar_monitoreo.sh
```

1. Definir `GRAFANA_ADMIN_PASSWORD` (valor local, no versionado).
2. La API, en otra terminal (queda corriendo). Expone `GET /metrics`.
3. Levanta el monitoreo y muestra la tabla de targets (todos deben estar `up`).

Accesos (solo en `127.0.0.1`):

| Herramienta | URL |
|---|---|
| Grafana, dashboard del Fixture | http://localhost:3000/d/fixture2030 |
| Prometheus, targets | http://localhost:9090/targets |
| Prometheus, alertas | http://localhost:9090/alerts |
| Métricas de la API | http://localhost:8000/metrics |

Para ver tráfico en los paneles, ver `defensa/demo.md` (generador liviano del Hito 12).

## Verificación y prueba de falla

```bash
cd hito-13-monitoreo && .venv/bin/python scripts/verificar_targets.py --guardar
```

```bash
cd hito-13-monitoreo && .venv/bin/python scripts/ejecutar_prueba_controlada.py --base cassandra
```

1. Tabla de targets y estado de cada base; guarda `evidencia/prometheus_targets.json`.
2. ~4 minutos: tráfico liviano, `docker stop fixture2030-cassandra` durante 60 s, `docker start`, y
   observación de la recuperación. Guarda la línea de tiempo, las series de Prometheus, las alertas, un
   gráfico y capturas de Grafana en `evidencia/prueba_de_falla_cassandra_<fecha>/`. No borra volúmenes ni datos.

## Limpieza

```bash
cd hito-13-monitoreo && bash scripts/limpiar_entorno.sh
```

Detiene Prometheus, Grafana y los exporters. Con `--datos` borra también el historial de métricas. Las seis
bases y sus datos no se tocan.
