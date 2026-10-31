"""Adaptador de InfluxDB 3 Core (Hito 8): estadísticas por equipo en una ventana temporal.

Usa la API HTTP /api/v3/query_sql con parámetros ($partido, $desde, $hasta): los valores del
cliente nunca se concatenan en el SQL.
"""
from datetime import datetime

import httpx

from app.config import config
from app.errores import DependenciaNoDisponible, DependenciaTimeout

_cliente = httpx.Client(base_url=config.influx_url, timeout=config.timeout_s,
                        headers={"Authorization": f"Bearer {config.influx_token}"})

_RAW = """
SELECT time, equipo_id, posesion_pct, pases_completados, tiros
FROM estadisticas_equipo
WHERE partido_id = $partido AND time >= to_timestamp($desde) AND time < to_timestamp($hasta)
ORDER BY time, equipo_id
"""

# posesion_pct es un valor de muestra -> promedio; pases y tiros son acumulados -> máximo del minuto.
_MINUTO = """
SELECT date_bin(INTERVAL '1 minute', time) AS time, equipo_id,
       round(avg(posesion_pct), 2) AS posesion_pct, max(pases_completados) AS pases_completados, max(tiros) AS tiros
FROM estadisticas_equipo
WHERE partido_id = $partido AND time >= to_timestamp($desde) AND time < to_timestamp($hasta)
GROUP BY 1, equipo_id
ORDER BY 1, equipo_id
"""


def _sql(q: str, params: dict) -> list[dict]:
    cuerpo = {"db": config.influx_database, "q": q, "format": "json", "params": params}
    try:
        respuesta = _cliente.post("/api/v3/query_sql", json=cuerpo)
    except httpx.TimeoutException as e:
        raise DependenciaTimeout("InfluxDB", type(e).__name__)
    except httpx.HTTPError as e:
        raise DependenciaNoDisponible("InfluxDB", type(e).__name__)
    # 401/403: token inválido; 404: database inexistente; 5xx: error del servidor.
    if respuesta.status_code in (401, 403, 404) or respuesta.status_code >= 500:
        raise DependenciaNoDisponible("InfluxDB", f"HTTP {respuesta.status_code}")
    respuesta.raise_for_status()
    return respuesta.json()


def consultar(partido: str, desde: datetime, hasta: datetime, agregacion: str) -> list[dict]:
    filas = _sql(_RAW if agregacion == "raw" else _MINUTO,
                 {"partido": partido, "desde": desde.isoformat(), "hasta": hasta.isoformat()})
    return [{"time": f["time"] + "Z", "equipoId": f["equipo_id"], "posesionPct": f.get("posesion_pct"),
             "pasesCompletados": f.get("pases_completados"), "tiros": f.get("tiros")}
            for f in filas]


def ping() -> None:
    """Token, database y motor SQL: una consulta constante, sin leer datos."""
    _sql("SELECT 1", {})
