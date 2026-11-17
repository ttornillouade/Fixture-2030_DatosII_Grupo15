# Inventario de componentes y su monitoreo (5.1)

Regla del inventario: una base figura como **monitoreada** solo si hay una métrica que Prometheus
efectivamente recolecta (verificable en `evidencia/prometheus_targets.json` y en Grafana). Lo que no se
pudo instrumentar figura como limitación, no como monitoreado.

| Componente | Modelo | Función en el Fixture | Puerto (127.0.0.1) | Mecanismo de monitoreo | Métricas seleccionadas | Riesgo que se observa | Limitaciones |
|---|---|---|---|---|---|---|---|
| **API FastAPI** (`hito-10-api`) | — (integración) | Única puerta de entrada: un endpoint por caso de uso, un adaptador por base | 8000 (`/metrics`) | **Directo**: la API publica sus métricas con `prometheus_client` (`app/metricas.py`) | `fixture2030_http_requests_total`, `fixture2030_http_request_duration_seconds` (por ruta, base y status), `fixture2030_dependencia_up`, `fixture2030_dependencia_ping_segundos`, `fixture2030_cache_comentarios_total` | Latencia y errores que ve el usuario; qué base los causa | Corre en la notebook (no en Docker): Prometheus la alcanza por `host.docker.internal`. No mide CPU propia (se mide con `psutil` en el Hito 12) |
| **MongoDB** | Documental | Equipos y jugadores (ficha y plantel paginado) | 27017 | **Exporter** `percona/mongodb_exporter` + sonda TCP + ping de la API | `mongodb_up`, `mongodb_op_counters_total{type}`, `mongodb_connections{state}`, `probe_success` | Caída, saturación de conexiones, consultas sin índice (opcounters altos con pocas requests) | Sin replica set: no hay métricas de replicación ni de elección de primario |
| **Redis** | Clave-valor | Sesiones con TTL (Hito 7) y caché del feed de comentarios (Hito 12) | 6379 | **Exporter** `oliver006/redis_exporter` + sonda TCP + ping de la API | `redis_up`, `redis_commands_processed_total`, `redis_memory_used_bytes`, `redis_connected_clients`, aciertos de caché (API) | Memoria cerca de `maxmemory` 256 MB con `noeviction` → escrituras rechazadas (no se pueden crear sesiones) | Instancia única: sin métricas de réplica/Sentinel |
| **Cassandra** | Columnar (wide-column) | Comentarios por partido y por usuario (Hito 6) | 9042 | **Sonda TCP** (blackbox) + ping de la API + métricas de la API para la ruta de comentarios (`fuente="Cassandra"`) | `probe_success`, `probe_duration_seconds`, `fixture2030_dependencia_up{base="Cassandra"}`, latencia y 503/504 de `/partidos/{codigo}/comentarios` | Caída del nodo, timeouts de lectura/escritura (504) | **Sin métricas internas** (compactación, pending tasks, latencia por tabla): requieren el agente JMX exporter dentro del contenedor. Propuesto, no implementado |
| **Neo4j** | Grafo | Partidos que jugó un jugador y rivales (Hito 5) | 7687 (Bolt), 7474 | **Sonda TCP** + ping de la API + métricas de la ruta `/jugadores/{codigo}/partidos` | `probe_success`, `fixture2030_dependencia_up{base="Neo4j"}`, latencia de la ruta | Caída, consultas de recorrido lentas | El endpoint Prometheus de Neo4j es solo de la edición Enterprise; la imagen usada es Community |
| **InfluxDB 3 Core** | Series temporales | Estadísticas de equipo por partido (Hito 8) | 8181 | **Sonda HTTP** a `/health` (sin token) + sonda TCP + ping de la API | `probe_success{job="sonda_http"}`, `probe_http_status_code`, `fixture2030_dependencia_up{base="InfluxDB"}` | Caída, token inválido (la sonda `/health` responde pero la API marca la base caída) | InfluxDB expone `/metrics`, pero exige el token de administrador; no se configuró para no poner el token en la configuración de Prometheus |
| **IRIS** | Multimodelo (objetos + SQL) | Partido como entidad compleja con sus eventos y transiciones de estado (Hito 9) | 1972, 52773 | **Sonda TCP** + ping de la API + métricas de las rutas `/partidos/{codigo}/detalle` y `/estado` | `probe_success`, `fixture2030_dependencia_up{base="IRIS"}`, latencia y 409 de la ruta de estado | Caída, transiciones rechazadas | `/api/monitor/metrics` de IRIS requiere habilitar la aplicación web con credenciales; no se hizo en el laboratorio |
| **Prometheus** | — | Recolecta y evalúa reglas | 9090 | Se monitorea a sí mismo (`job="prometheus"`) | `up`, `prometheus_tsdb_head_series` | Pérdida de visibilidad | Una sola instancia, retención 7 días / 1 GB |
| **Grafana** | — | Visualización | 3000 | Healthcheck de Docker (`/api/health`) | — | — | No se scrapean métricas de Grafana |
| **Blackbox exporter** | — | Sondas TCP/HTTP | 9115 (interno) | `job="blackbox"` | `up` | Si cae, todas las sondas quedan sin dato (no en 0) | — |

## Qué se mide directamente, qué por exporter y qué se infiere (RNF3)

| Tipo | Ejemplos | Cómo leerlo |
|---|---|---|
| **Medido por la aplicación** | latencia por ruta, requests por status, estado de cada base según su driver, aciertos de caché | Es lo que vive el usuario de la API. Incluye el tiempo de espera dentro de la API |
| **Medido por exporter** | operaciones y conexiones de MongoDB, memoria y comandos de Redis | Es la visión interna del producto. No dice nada de la API |
| **Medido por sonda sintética** | `probe_success`, `probe_duration_seconds` | Solo dice si el puerto acepta conexiones desde la red de Docker, no si la base funciona |
| **Inferido** | "la latencia está en la base y no en la API" | Se infiere comparando el ping por base con la latencia dentro de la API; no hay trazas distribuidas |
| **Propuesto, no implementado** | métricas internas de Cassandra (JMX), Neo4j Enterprise, IRIS `/api/monitor`, CPU por contenedor (cAdvisor), Alertmanager | Ver `limitaciones_y_evidencia.md` |
