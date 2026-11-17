# Grafana del Fixture 2030

Todo se provisiona desde archivos (no hay que configurar nada a mano):

| Archivo | Qué provisiona |
|---|---|
| `provisioning/datasources/prometheus.yml` | Fuente de datos Prometheus (`http://prometheus:9090`, uid `prometheus-fixture2030`) |
| `provisioning/dashboards/fixture2030.yml` | Proveedor de dashboards desde `dashboards/` (carpeta *Fixture 2030*, no editable desde la UI) |
| `dashboards/fixture2030.json` | Dashboard **Fixture 2030 — Plataforma** (uid `fixture2030`) |
| `generar_dashboard.py` | Genera el JSON anterior (dashboard como código) |

Acceso: `http://localhost:3000/d/fixture2030`. La lectura es anónima (rol *Viewer*, solo laboratorio); para
administrar, usuario `admin` con la contraseña de `../.env` (no versionada).

## Paneles

| Fila | Panel | Pregunta que responde | Consulta | Unidad |
|---|---|---|---|---|
| 1. Disponibilidad | Bases según la API | ¿Cada base responde a su driver? | `fixture2030_dependencia_up` | ARRIBA/CAÍDA |
| | Puerto TCP de cada base | ¿El puerto acepta conexiones? | `probe_success{job="sonda_tcp"}` | ARRIBA/CAÍDA |
| | Targets de Prometheus | ¿Se están leyendo las métricas? | `up{job=~"api\|redis\|mongodb"}` | ARRIBA/CAÍDA |
| 2. API | Requests por segundo, por base | ¿Cuánto tráfico atiende cada base? (volumen) | `fixture2030:api_requests:rate1m` | req/s |
| | Latencia p95 dentro de la API | ¿Cuánto tarda? (con umbral de 300 ms) | `fixture2030:api_latencia_p95:1m` + p50 global | s |
| | Respuestas no exitosas | ¿Qué falla y con qué código? | `rate(...{status=~"4..\|5.."}[1m])` por status y base | req/s |
| 3. Comparación | Tiempo de ping por base | ¿Qué base es más lenta en reposo? | `fixture2030_dependencia_ping_segundos` | s |
| | Operaciones en Redis y MongoDB | ¿Qué hace cada base por dentro? (exporters) | `redis_commands_processed_total`, `mongodb_op_counters_total` | ops/s |
| | Caché de comentarios: aciertos | ¿Funciona la optimización del Hito 12? | hits / total | % |
| | Duración de la sonda TCP | ¿Es la red/contenedor o la base? | `probe_duration_seconds` | s |
| | Recursos de Redis y MongoDB | ¿Se acerca Redis a su límite de 256 MB? | `redis_memory_used_bytes`, `mongodb_connections` | bytes / conexiones |
| | Cómo leer este dashboard | Umbrales interpretados y qué mirar primero | — | — |

Rango por defecto: últimos 15 minutos, refresco cada 5 s. Cada panel tiene una descripción (ícono ⓘ) con
la métrica, la ventana y la unidad.

## Modificar el dashboard

```bash
python grafana/generar_dashboard.py
```

Grafana relee el archivo en ~10 s. No editar el JSON a mano ni desde la UI (está bloqueado:
`allowUiUpdates: false`), para que el dashboard versionado sea siempre el que se ve.
