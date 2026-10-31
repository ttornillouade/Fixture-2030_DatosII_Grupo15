"""Cadena completa cliente HTTP -> API -> adaptador -> producto, con las rutas del Hito 10.

Solo rutas de lectura (no modifica datos). Para cada una registra método y path, dependencia, status,
duración, requestId y la línea del log de la API con ese requestId (si API_LOG apunta a la salida de
la API). Distingue: API no alcanzable, dependencia fallida (503/504), recurso inexistente (404),
respuesta vacía válida (200 vacío), error de validación (400) y operación exitosa (200).
Uso: python prueba_api.py [producto ...]
"""
import sys
import time
from pathlib import Path

import httpx

from comun import RAIZ, Registro, cargar_config

c = cargar_config()
API = c.get("API_URL", "http://localhost:8000")
LOG = RAIZ / c["API_LOG"] if c.get("API_LOG") else None
B = "2030-06-08T20:00:00Z"
V = "desde=2030-06-08T16:00:00Z&hasta=2030-06-08T16:00:02Z"

# producto -> [(path, status esperado, qué muestra)]
RUTAS = {
    "api": [("/salud", 200, "liveness: el proceso responde sin consultar bases"),
            ("/salud/dependencias", 200, "diagnóstico: un ping por base")],
    "mongodb": [("/equipos/E010", 200, "operación exitosa"),
                ("/equipos/E999", 404, "recurso inexistente"),
                ("/jugadores?equipoCodigo=E999", 200, "respuesta vacía válida"),
                ("/equipos/X1", 400, "error de validación: no llega a la base")],
    "neo4j": [("/jugadores/E001-J09/partidos", 200, "operación exitosa"),
              ("/jugadores/E999-J99/partidos", 404, "recurso inexistente")],
    "cassandra": [(f"/partidos/P001/comentarios?bucket={B}&limit=2", 200, "operación exitosa"),
                  ("/partidos/P001/comentarios?bucket=2030-06-08T20:03:00Z", 400, "error de validación: bucket desalineado")],
    "redis": [("/sesiones/s-demo-001", 200, "operación exitosa (requiere preparar_datos_demo.sh)"),
              ("/sesiones/s-no-existe", 404, "clave ausente o expirada: Redis responde")],
    "influxdb": [(f"/partidos/P001/estadisticas?{V}", 200, "operación exitosa"),
                 ("/partidos/P001/estadisticas?desde=2031-06-08T16:00:00Z&hasta=2031-06-08T16:10:00Z", 200,
                  "respuesta vacía válida: ventana sin puntos")],
    "iris": [("/partidos/P001/detalle", 200, "operación exitosa"),
             ("/partidos/P999/detalle", 404, "recurso inexistente")],
}


def linea_de_log(request_id: str) -> str:
    if not LOG or not LOG.exists():
        return "sin log (iniciar la API con su salida en API_LOG)"
    time.sleep(0.05)  # la API escribe la línea al terminar la respuesta
    for linea in reversed(LOG.read_text(encoding="utf-8", errors="replace").splitlines()):
        if request_id in linea:
            return linea.split(" INFO api ", 1)[-1]
    return "requestId no encontrado en el log"


def interpretar(status: int, cuerpo) -> str:
    if status == 200 and isinstance(cuerpo, dict):
        vacio = [k for k in ("items", "puntos", "partidos", "dependencias") if k in cuerpo and not cuerpo[k]]
        if vacio:
            return f"200 vacío ({vacio[0]}=[]): ausencia válida"
        if "dependencias" in cuerpo:
            return f"estado {cuerpo['estado']}: " + ", ".join(f"{d['nombre']}={d['estado']}" for d in cuerpo["dependencias"])
        return "200 con datos"
    if isinstance(cuerpo, dict) and "code" in cuerpo:
        return f"{status} {cuerpo['code']}"
    return str(status)


cliente = httpx.Client(base_url=API, timeout=c["TIMEOUT_S"] + 5)
productos = sys.argv[1:] or list(RUTAS)
try:
    cliente.get("/salud")
except httpx.HTTPError as e:
    for producto in productos:
        Registro(producto).anotar("api", f"GET {API}", "FALLA",
                                  f"API no alcanzable ({type(e).__name__}): no se puede evaluar la cadena")
    sys.exit(0)

for producto in productos:
    r = Registro(producto)
    for path, esperado, muestra in RUTAS[producto]:
        inicio = time.perf_counter()
        respuesta = cliente.get(path)
        ms = (time.perf_counter() - inicio) * 1000
        request_id = respuesta.headers.get("X-Request-ID", "-")
        cuerpo = respuesta.json() if respuesta.headers.get("content-type", "").startswith("application/json") else None
        resultado = "OK" if respuesta.status_code == esperado else "FALLA"
        r.anotar("api", f"GET {path}", resultado,
                 f"{interpretar(respuesta.status_code, cuerpo)} (esperado {esperado}: {muestra}) | {request_id} | "
                 f"log: {linea_de_log(request_id)}", ms, tipo="capa" if esperado == 200 and "vacía" not in muestra else "contraste")
