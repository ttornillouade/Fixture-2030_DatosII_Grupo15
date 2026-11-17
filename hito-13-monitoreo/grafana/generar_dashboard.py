"""Genera grafana/dashboards/fixture2030.json (dashboard como código).

Editar este script y volver a correrlo en lugar de editar el JSON a mano:
    python grafana/generar_dashboard.py
Grafana relee el archivo provisionado cada ~10 s (no hace falta reiniciarlo).
"""
import json
from pathlib import Path

DS = {"type": "prometheus", "uid": "prometheus-fixture2030"}
_id = 0


def _sig():
    global _id
    _id += 1
    return _id


def fila(titulo, y):
    return {"type": "row", "title": titulo, "id": _sig(), "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def objetivo(expr, leyenda, ref="A"):
    return {"datasource": DS, "expr": expr, "legendFormat": leyenda, "refId": ref, "range": True}


def estado(titulo, descripcion, expr, leyenda, x, y, w, h=5, textos=("CAÍDA", "ARRIBA")):
    return {
        "type": "stat", "title": titulo, "description": descripcion, "id": _sig(), "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": [objetivo(expr, leyenda)],
        "options": {"colorMode": "background", "graphMode": "none", "textMode": "value_and_name",
                    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "orientation": "horizontal", "text": {"titleSize": 13, "valueSize": 15}},
        "fieldConfig": {"defaults": {
            "mappings": [{"type": "value", "options": {"0": {"text": textos[0], "color": "red"},
                                                       "1": {"text": textos[1], "color": "green"}}}],
            "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None},
                                                         {"color": "green", "value": 1}]},
            "noValue": "SIN DATOS"}, "overrides": []}}


def serie(titulo, descripcion, objetivos, unidad, x, y, w, h=8, umbral=None, minimo=0, apilar=False):
    defaults = {"unit": unidad, "min": minimo,
                "custom": {"drawStyle": "line", "lineWidth": 2, "fillOpacity": 10, "showPoints": "never",
                           "spanNulls": False, "stacking": {"mode": "normal" if apilar else "none"},
                           "thresholdsStyle": {"mode": "line+area" if umbral is not None else "off"}},
                "thresholds": {"mode": "absolute",
                               "steps": [{"color": "green", "value": None}] +
                                        ([{"color": "red", "value": umbral}] if umbral is not None else [])}}
    return {"type": "timeseries", "title": titulo, "description": descripcion, "id": _sig(), "datasource": DS,
            "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "targets": [objetivo(e, l, chr(65 + i)) for i, (e, l) in enumerate(objetivos)],
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "max"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}},
            "fieldConfig": {"defaults": defaults, "overrides": []}}


def texto(titulo, contenido, x, y, w, h):
    return {"type": "text", "title": titulo, "id": _sig(), "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "options": {"mode": "markdown", "content": contenido}}


paneles = [
    fila("1. Disponibilidad (¿está cada componente arriba?)", 0),
    estado("Bases según la API (ping de aplicación)",
           "fixture2030_dependencia_up: la API repite cada 15 s el diagnóstico de /salud/dependencias "
           "(un ping por base con su driver). 1 = respondió, 0 = falló (503/504). Métrica de aplicación.",
           "fixture2030_dependencia_up", "{{base}}", 0, 1, 12),
    estado("Puerto TCP de cada base (sonda blackbox)",
           "probe_success del blackbox exporter: abre una conexión TCP al puerto de cada base desde la red "
           "de Docker. Distingue 'la base no acepta conexiones' de 'la API no puede usarla'.",
           'probe_success{job="sonda_tcp"}', "{{componente}}", 12, 1, 8),
    estado("Targets de Prometheus",
           "up: 1 si Prometheus pudo leer /metrics del target en el último scrape (5 s).",
           'up{job=~"api|redis|mongodb"}', "{{job}}", 20, 1, 4),

    fila("2. API: volumen, latencia y errores (métricas de aplicación)", 6),
    serie("Requests por segundo, por base",
          "rate de fixture2030_http_requests_total en ventanas de 1 min, agrupado por la base que atiende "
          "el endpoint (etiqueta fuente). Unidad: req/s.",
          [("fixture2030:api_requests:rate1m", "{{fuente}}")], "reqps", 0, 7, 8, apilar=True),
    serie("Latencia p95 dentro de la API, por base",
          "histogram_quantile(0.95) del histograma fixture2030_http_request_duration_seconds, ventana 1 min. "
          "Línea roja: umbral de 300 ms de la alerta LatenciaComentariosAlta (comentarios).",
          [("fixture2030:api_latencia_p95:1m", "p95 {{fuente}}"),
           ('histogram_quantile(0.50, sum by (le) (rate(fixture2030_http_request_duration_seconds_bucket[1m])))',
            "p50 global")],
          "s", 8, 7, 8, umbral=0.3),
    serie("Respuestas no exitosas por código",
          "Requests con status 4xx/5xx por segundo (ventana 1 min). 400/404/409: error del cliente o regla de "
          "negocio. 503: la base rechazó la conexión. 504: la base no respondió en TIMEOUT_S (3 s).",
          [('sum by (status, fuente) (rate(fixture2030_http_requests_total{status=~"4..|5.."}[1m]))',
            "{{status}} {{fuente}}")], "reqps", 16, 7, 8),

    fila("3. Comparación entre bases y subsistemas", 15),
    serie("Tiempo de ping por base (desde la API)",
          "fixture2030_dependencia_ping_segundos: duración del último ping de diagnóstico. Compara el costo "
          "base de cada producto, sin carga de negocio. Una base caída queda en ~3 s (TIMEOUT_S) o sin dato.",
          [("fixture2030_dependencia_ping_segundos", "{{base}}")], "s", 0, 16, 8),
    serie("Operaciones por segundo en Redis y MongoDB (exporters)",
          "Métricas de infraestructura de los exporters: comandos procesados por Redis "
          "(redis_commands_processed_total) y operaciones de MongoDB por tipo (mongodb_op_counters_total). "
          "Ventana 1 min.",
          [("rate(redis_commands_processed_total[1m])", "Redis comandos"),
           ('sum by (type) (rate(mongodb_op_counters_total{type!="command"}[1m]))', "MongoDB {{type}}")],
          "ops", 8, 16, 8),
    serie("Caché de comentarios (Hito 12): aciertos",
          "Proporción de lecturas de la primera página de comentarios que se resolvieron en Redis sin ir "
          "a Cassandra. Sin dato = caché desactivada o sin tráfico.",
          [('sum(rate(fixture2030_cache_comentarios_total{resultado="hit"}[1m])) / '
            'sum(rate(fixture2030_cache_comentarios_total[1m]))', "aciertos")],
          "percentunit", 16, 16, 8),
    serie("Duración de la sonda TCP por base",
          "probe_duration_seconds del blackbox: tiempo para abrir la conexión TCP. Separa red/contenedor "
          "de la lógica de la base.", [('probe_duration_seconds{job="sonda_tcp"}', "{{componente}}")],
          "s", 0, 24, 8),
    serie("Recursos de Redis y MongoDB",
          "Memoria usada por Redis (límite configurado: 256 MB, noeviction) y conexiones abiertas en MongoDB.",
          [("redis_memory_used_bytes", "Redis memoria"), ('mongodb_connections{state="current"}', "MongoDB conexiones")],
          "short", 8, 24, 8),
    texto("Cómo leer este dashboard",
          "**Umbrales interpretados** (detalle en `docs/alertas_y_umbral.md`):\n\n"
          "- Disponibilidad en rojo **> 30 s** → alerta `BaseNoDisponible` (crítica).\n"
          "- p95 de comentarios **> 300 ms durante 2 min** → `LatenciaComentariosAlta`.\n"
          "- 5xx **> 2 %** de las requests durante 1 min → `ErroresServidorAltos`.\n\n"
          "**Primero mirar:** si sube la latencia, comparar *ping por base* (¿la base?) con *p95 dentro de "
          "la API* (¿la API?). Si la sonda TCP está verde y la API marca la base caída, el problema está en "
          "el driver/credenciales, no en el contenedor.\n\n"
          "Rango sugerido: últimos 15 min, refresco 5 s.", 16, 24, 8, 8),
]

dashboard = {
    "uid": "fixture2030", "title": "Fixture 2030 — Plataforma", "tags": ["fixture2030", "hito13"],
    "timezone": "browser", "schemaVersion": 41, "version": 1, "editable": False, "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"}, "panels": paneles,
    "description": "Disponibilidad, latencia, volumen y errores de la API del Fixture 2030 y de sus bases.",
}
destino = Path(__file__).parent / "dashboards" / "fixture2030.json"
destino.parent.mkdir(exist_ok=True)
destino.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"{destino} ({len(paneles)} paneles)")
