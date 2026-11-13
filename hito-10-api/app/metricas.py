"""Métricas Prometheus de la API (Hito 13), expuestas en GET /metrics.

Métricas de APLICACIÓN (las mide la API, no un exporter):
  fixture2030_http_requests_total{metodo,ruta,fuente,status}       requests atendidas (counter)
  fixture2030_http_request_duration_seconds{metodo,ruta,fuente}    duración dentro de la API (histograma)
  fixture2030_dependencia_up{base}                                 1 si el último ping a la base respondió, 0 si no
  fixture2030_dependencia_ping_segundos{base}                      duración del último ping
  fixture2030_cache_comentarios_total{resultado}                   hit / miss / error de la caché del Hito 12

`ruta` es la plantilla de la ruta (/partidos/{codigo}/comentarios), no la URL: así la cantidad de
series no crece con cada partido o sesión. No se registran parámetros, cuerpos ni credenciales.

El estado de las dependencias lo calcula un hilo que repite el diagnóstico de /salud/dependencias
cada METRICAS_SONDEO_S segundos (15 por defecto), fuera del camino de las requests.

Con varios procesos uvicorn (--workers, Hito 12) cada proceso tiene sus contadores: si está definida
PROMETHEUS_MULTIPROC_DIR, se usa el modo multiproceso de prometheus_client y /metrics suma todos.
"""
import os
import threading
import time

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from prometheus_client import multiprocess

_MULTI = bool(os.environ.get("PROMETHEUS_MULTIPROC_DIR"))

REQUESTS = Counter("fixture2030_http_requests_total", "Requests atendidas por la API",
                   ["metodo", "ruta", "fuente", "status"])
DURACION = Histogram("fixture2030_http_request_duration_seconds", "Duración de la request dentro de la API",
                     ["metodo", "ruta", "fuente"],
                     buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))
DEPENDENCIA_UP = Gauge("fixture2030_dependencia_up", "1 si el último ping a la base respondió, 0 si falló",
                       ["base"], multiprocess_mode="max")
DEPENDENCIA_PING = Gauge("fixture2030_dependencia_ping_segundos", "Duración del último ping a la base",
                         ["base"], multiprocess_mode="max")
CACHE = Counter("fixture2030_cache_comentarios_total", "Lecturas de la primera página de comentarios por caché",
                ["resultado"])


def registrar(metodo: str, ruta: str, fuente: str, status: int, segundos: float) -> None:
    REQUESTS.labels(metodo, ruta, fuente, str(status)).inc()
    DURACION.labels(metodo, ruta, fuente).observe(segundos)


def exponer() -> tuple[bytes, str]:
    if _MULTI:
        registro = CollectorRegistry()
        multiprocess.MultiProcessCollector(registro)
        return generate_latest(registro), CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST


def iniciar_sondeo(diagnostico) -> None:
    """diagnostico: servicios.salud_dependencias. Las bases sin secreto configurado no se exportan."""
    intervalo = float(os.environ.get("METRICAS_SONDEO_S", "15"))

    def ciclo():
        while True:
            try:
                for d in diagnostico()["dependencias"]:
                    if d["estado"] == "not_configured":
                        continue
                    DEPENDENCIA_UP.labels(d["nombre"]).set(1 if d["estado"] == "up" else 0)
                    DEPENDENCIA_PING.labels(d["nombre"]).set((d["ms"] or 0) / 1000)
            except Exception:  # el sondeo nunca debe tirar abajo la API
                pass
            time.sleep(intervalo)

    threading.Thread(target=ciclo, daemon=True, name="metricas-sondeo").start()
