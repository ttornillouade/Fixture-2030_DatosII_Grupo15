# Evidencia y limitaciones (RF10, RF11, RF12, RNF3, RNF8)

Todo lo de este documento se ejecutó el 2026-11-13 en el laboratorio descrito en
`hito-12-carga-optimizacion/compose-o-instrucciones-del-entorno.md` (PC con 6 núcleos, Windows 10, Docker
Desktop, un contenedor por base). Se distingue **medido**, **estimado** y **propuesto**.

## 1. Targets verificados (medido)

`evidencia/prometheus_targets.json`: **13/13 targets UP** (api, redis, mongodb, prometheus, blackbox, 6 sondas
TCP, 2 sondas HTTP) y las 6 bases con `fixture2030_dependencia_up = 1` y `probe_success = 1`. Reglas cargadas:
3 de registro y 5 alertas, todas con `health = ok`.

## 2. Prueba de falla controlada: Cassandra detenida (medido)

Procedimiento (`scripts/ejecutar_prueba_controlada.py`): tráfico liviano y constante con un hilo por base
(Cassandra, MongoDB, Redis; ~4 req/s cada uno), 60 s normales, `docker stop fixture2030-cassandra`, ~60 s con
la base detenida, `docker start`, espera del healthcheck y 90 s de observación. Las series salen de Prometheus
(paso de 5 s); los tiempos tienen esa resolución.

| Corrida | Qué es | Carpeta |
|---|---|---|
| 1 | Cliente de un solo hilo: **artefacto** (el cliente se frenaba con Cassandra y dejaba de enviar a las otras bases). Se conserva con su explicación | `evidencia/prueba_de_falla_cassandra_trafico_secuencial_20261113T173806Z/` |
| 2 | **Antes** de la mejora (API del commit `f486b51`) | `evidencia/prueba_de_falla_cassandra_20261113T174247Z/` |
| 3 | **Después** del corte rápido en el adaptador de Cassandra (commit `76235b1`) | `evidencia/prueba_de_falla_cassandra_20261113T174816Z/` |

Cada carpeta tiene `eventos.json` (línea de tiempo y consultas PromQL usadas), `series.csv`, `alertas.json`,
`trafico.json` (lo que vio el cliente), `prueba_de_falla.png` (gráfico) y `grafana_prueba_completa.png`
(captura del dashboard con el rango de la prueba, tomada con un navegador headless).

### Qué se observó

| Observación | Antes (corrida 2) | Después (corrida 3) |
|---|---|---|
| Sonda TCP detecta la caída | 5 s después del `docker stop` | 10 s (resolución de 5 s) |
| La API marca Cassandra caída (`dependencia_up = 0`) | **30 s** | **5 s** |
| Alertas activas al final de la caída | `BaseNoDisponible`, `SondaTCPFallando` | las mismas |
| Respuestas de comentarios durante la caída | 18 respuestas 503 | 207 respuestas 503 |
| Latencia de esos 503 (log de la API) p50 / p95 / máx. | **4.081 / 7.952 / 7.952 ms** | **3 / 11 / 4.108 ms** |
| `GET /salud/dependencias` durante la caída | 6,54 s | 3,04 s |
| MongoDB y Redis durante la caída | 100 % 200 (913 y 894 requests, máx. 38 y 76 ms) | 100 % 200, tráfico constante en el gráfico |
| Cassandra sana tras `docker start` | 18,6 s | 17,9 s |
| La API vuelve a marcarla arriba, después de "healthy" | 7 s | 13 s |
| Reinicio de la API necesario | no | no |

### Interpretación

- **Aislamiento (objetivo de distribución del TPO)**: la caída de una base afecta solo a sus endpoints. MongoDB
  y Redis siguieron respondiendo en milisegundos. Es consecuencia directa de "un endpoint, una base".
- **Hallazgo (antes)**: con Cassandra detenida, cada request intentaba volver a crear la conexión del driver bajo
  un lock compartido (~4 s por intento, primero por IPv6 y después por IPv4) y las demás esperaban en fila. La API
  respondía el código correcto (503), pero **tarde**: hasta 8 s, por encima del `TIMEOUT_S` de 3 s del Hito 11.
  El propio diagnóstico de salud quedaba en esa fila: la API tardó 30 s en reportar la caída en Prometheus.
- **Mejora transversal implementada y medida (RF12)**: corte rápido (circuit breaker) en
  `hito-10-api/app/adaptadores/cassandra.py`. Después de un fallo de conexión, durante `CASSANDRA_REINTENTO_S`
  (5 s) responde 503 sin intentar conectar, y si otra request ya está conectando no espera más de `TIMEOUT_S`.
  Resultado: los 503 pasan de segundos a milisegundos, la API puede rechazar 10 veces más requests en el mismo
  tiempo sin acumular hilos esperando, y la caída se ve en Prometheus en 5 s en lugar de 30 s.
- **Trade-off**: la recuperación se demora hasta `CASSANDRA_REINTENTO_S` más (13 s en lugar de 7 s después de que
  el contenedor está sano), porque durante la ventana de corte no se reintenta. Se acepta: 5 s más de
  indisponibilidad contra minutos de requests colgadas.
- **Pendiente**: el mismo patrón se aplicaría a Neo4j e IRIS (sus drivers no tienen timeout de lectura; el Hito 10
  los envuelve en hilos con límite, `adaptadores/limite.py`). No se implementó ni se midió.

## 3. Relación con los objetivos del TPO (RF11)

| Objetivo | Evidencia medida | Dónde |
|---|---|---|
| Concurrencia | 60 usuarios virtuales: 163 req/s en la línea base; 273 req/s optimizado | Hito 12 `comparacion.md` |
| Throughput | por base, en el dashboard (`fixture2030:api_requests:rate1m`) | Grafana, fila 2 |
| Latencia | p95 dentro de la API por base; p95 de comentarios 399 → 186 ms (Hito 12) | Grafana, Hito 12 |
| Disponibilidad | caída detectada por dos señales independientes (driver y TCP), alertas a los 30 s | prueba de falla |
| Distribución | fallas aisladas por base | prueba de falla (MongoDB/Redis 100 % OK) |
| Recuperación | sin reiniciar la API; 7-13 s después de que la base está sana | prueba de falla |

## 4. Qué se mide, qué se infiere y qué se propone (RNF3)

| | Ejemplos |
|---|---|
| **Medido directamente** por la API | requests, latencia, status por ruta y base; estado de cada base por su driver; aciertos de caché |
| **Medido por exporter** | operaciones, conexiones y estado de MongoDB; memoria, comandos y clientes de Redis |
| **Medido por sonda** | conexión TCP a las 6 bases; HTTP a `/health` de InfluxDB y `/salud` de la API |
| **Inferido** | "el problema está en la API y no en la base": comparando ping por base con la latencia dentro de la API; no hay trazas distribuidas |
| **Propuesto, no implementado** | JMX exporter para Cassandra; endpoint de métricas de IRIS (`/api/monitor`); InfluxDB `/metrics` con token desde un archivo de credenciales; cAdvisor para CPU por contenedor; Alertmanager; corte rápido en Neo4j e IRIS |

## 5. Limitaciones

1. **Un nodo por base**: la prueba detiene la base entera. No se probó la caída de **un** nodo con la base en
   servicio (requiere RF=3, replica set, etc.). Es la limitación más importante para la defensa.
2. **Sin métricas internas de Cassandra, Neo4j, InfluxDB e IRIS**: de esas bases solo se ve disponibilidad (TCP y
   driver) y el efecto en la API. Una compactación lenta de Cassandra, por ejemplo, solo se vería como latencia.
3. **Resolución**: scraping cada 5 s y diagnóstico de la API cada 15 s: los tiempos de detección tienen esa
   granularidad.
4. **La API corre fuera de Docker**: Prometheus la alcanza por `host.docker.internal`; si la notebook cambia de red
   o firewall, ese target puede caer sin que la API esté caída (lo detecta `TargetDeMonitoreoCaido`).
5. **Alertas sin notificación**: se ven en Prometheus y Grafana; no avisan a nadie (no hay Alertmanager).
6. **Umbrales experimentales**: salen de mediciones en una notebook (Hito 12), no de un acuerdo de servicio.
7. **Grafana con lectura anónima**: aceptable en `127.0.0.1` de laboratorio; en un entorno compartido habría que
   desactivarla.
8. **Capturas automáticas**: se generan con Edge/Chrome headless; si no hay navegador, el script lo informa y la
   captura se hace a mano.
