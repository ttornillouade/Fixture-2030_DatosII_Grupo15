# Métricas, configuración de Prometheus y consultas PromQL (RF2, RF4, RF8, 5.2)

## Configuración de Prometheus (`prometheus.yml`)

| Parámetro | Valor | Motivo |
|---|---|---|
| Intervalo de scraping | **5 s** (`scrape_interval`) | Laboratorio: la prueba de falla dura ~1 min; con 15 s habría 2-4 muestras de la caída. En producción, 15-30 s |
| Timeout de scraping | 4 s | Menor que el intervalo; mayor que el `TIMEOUT_S` de la API (3 s) |
| Evaluación de reglas | 5 s | Igual al scraping |
| Retención | 7 días o 1 GB (lo primero que se alcance) | Alcanza para la defensa; acota el disco de la notebook |
| Etiquetas externas | `entorno=laboratorio`, `sistema=fixture2030` | Distinguir estas series si se federan |

### Jobs, targets y componente observado

| Job | Target | Componente | Tipo | Etiquetas agregadas |
|---|---|---|---|---|
| `api` | `host.docker.internal:8000/metrics` | API FastAPI | métricas de aplicación | `componente=api`, `capa=aplicacion` |
| `redis` | `redis-exporter:9121` | Redis | exporter | `componente=redis`, `modelo=clave-valor`, `capa=base` |
| `mongodb` | `mongodb-exporter:9216` | MongoDB | exporter | `componente=mongodb`, `modelo=documental`, `capa=base` |
| `sonda_tcp` | `blackbox:9115/probe?module=tcp_connect&target=<base>:<puerto>` | las 6 bases | sonda sintética | `componente`, `modelo`; `instance` = base:puerto |
| `sonda_http` | `blackbox:9115/probe?module=http_2xx&target=...` | InfluxDB `/health`, API `/salud` | sonda sintética | `componente` |
| `prometheus`, `blackbox` | ellos mismos | monitoreo | autoobservación | `capa=monitoreo` |

La etiqueta **`fuente`** de las métricas de la API (`MongoDB`, `Neo4j`, `Cassandra`, `Redis`, `InfluxDB`,
`IRIS`, `Salud`) es la base que atiende cada endpoint (la misma que se registra en el log desde el Hito 10).
Es la que permite separar el comportamiento de cada base en el dashboard.

### Validar que un target está UP

1. `python scripts/verificar_targets.py` (o Prometheus → *Status → Target health*): estado `up` y sin error.
2. Consulta `up{job="api"}` = 1.
3. Para las sondas, `up` solo dice que el blackbox respondió: el estado real de la base es
   `probe_success{componente="cassandra"}` = 1.

### Investigar un target DOWN

1. Leer `lastError` del target (`verificar_targets.py` lo imprime):
   - `connection refused`: no hay proceso escuchando → ¿API detenida? ¿exporter caído? (`docker ps`).
   - `context deadline exceeded`: el target tarda más de 4 s → ver CPU de la notebook o del contenedor.
   - `no such host`: el contenedor no está en la red `hito-10-api_default` (`docker network inspect`).
2. Si el target está UP pero la base figura caída, comparar las dos señales:
   `probe_success` (¿acepta TCP?) vs `fixture2030_dependencia_up` (¿responde a su driver?). TCP arriba +
   driver abajo = credenciales, keyspace/base inexistente o base que acepta y no responde (pausada).
3. Cruzar con el log de la API: cada request fallida tiene `causa=` y `requestId` (Hito 11).

## Consultas PromQL explicadas (RF8)

Todas usan ventanas `rate(...[1m])` (o 30 s en la prueba de falla, para ver el cambio antes).

| # | Consulta | Qué mide | Unidad | Período |
|---|---|---|---|---|
| 1 | `sum by (fuente) (rate(fixture2030_http_requests_total[1m]))` (regla `fixture2030:api_requests:rate1m`) | Throughput de la API por base: requests completadas por segundo | req/s | ventana móvil de 1 min |
| 2 | `histogram_quantile(0.95, sum by (le, fuente) (rate(fixture2030_http_request_duration_seconds_bucket[1m])))` (regla `fixture2030:api_latencia_p95:1m`) | Percentil 95 de la duración dentro de la API, por base | segundos | 1 min |
| 3 | `sum by (fuente) (rate(fixture2030_http_requests_total{status=~"5.."}[1m])) / sum by (fuente) (rate(fixture2030_http_requests_total[1m]))` (regla `fixture2030:api_errores_5xx:ratio1m`) | Proporción de respuestas 5xx (503 base caída, 504 base lenta) | proporción 0-1 | 1 min |
| 4 | `fixture2030_dependencia_up` | Estado de cada base según su driver (último ping de la API) | 1/0 | instantáneo, se actualiza cada 15 s |
| 5 | `probe_success{job="sonda_tcp"}` | ¿El puerto de cada base acepta conexiones TCP? | 1/0 | cada scrape (5 s) |
| 6 | `sum(rate(fixture2030_cache_comentarios_total{resultado="hit"}[1m])) / sum(rate(fixture2030_cache_comentarios_total[1m]))` | Tasa de aciertos de la caché de comentarios (Hito 12) | proporción | 1 min |
| 7 | `rate(redis_commands_processed_total[1m])` | Comandos por segundo que ejecuta Redis (sesiones + caché) | ops/s | 1 min |
| 8 | `sum by (type) (rate(mongodb_op_counters_total{type!="command"}[1m]))` | Operaciones de MongoDB por tipo (query, getmore, insert...) | ops/s | 1 min |

**Por qué percentiles y no promedios**: el Hito 12 mostró que el promedio esconde la cola (con p50 de
~200 ms el p99 llegaba a ~490 ms). El histograma permite calcular p50, p95 y p99 en Prometheus. Los
buckets van de 5 ms a 10 s; la precisión del percentil está limitada al ancho del bucket (por ejemplo,
entre 250 y 500 ms el valor se interpola).

**Cuidado con `rate` de pocos datos**: con tráfico muy bajo (menos de una request por ventana) el p95 sale
`NaN` y el panel queda vacío: no significa que la API esté caída. Por eso la alerta de errores exige además
más de 1 req/s.

## Relación con los objetivos del TPO (RF11)

| Objetivo | Métrica que lo observa | Qué se vio en el laboratorio |
|---|---|---|
| Concurrencia | throughput (#1) durante la prueba del Hito 12 | La API con 1 proceso se satura en ~160 req/s con 60 usuarios; ver Hito 12 |
| Throughput | #1, #7, #8 | Por base: el tráfico de comentarios domina; Redis absorbe las lecturas repetidas con la caché |
| Latencia | #2 (p95 por base) | Ver `evidencia/` y el Hito 12 (antes/después de la optimización) |
| Disponibilidad | #4 y #5 | Prueba de falla: Cassandra detenida → `dependencia_up` y `probe_success` en 0; el resto de las bases sigue en 1 |
| Distribución | etiqueta `fuente`: cada base atiende su parte | Una base caída solo afecta sus endpoints (503), no toda la API |
| Recuperación | #3 vuelve a 0 y #4 a 1 después de `docker start` | Tiempos medidos en `evidencia/prueba_de_falla_*/eventos.json` |
