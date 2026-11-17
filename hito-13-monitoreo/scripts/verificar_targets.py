"""Verifica que cada target de Prometheus esté UP y que cada base tenga al menos una señal.

Procedimiento (RF2, 5.2):
  1. GET /api/v1/targets: por cada target, job, componente, estado (up/down), último error y duración.
  2. Por cada base: valor actual de fixture2030_dependencia_up (API) y probe_success (sonda TCP).
  3. Con --guardar, escribe evidencia/prometheus_targets.json (sin secretos: no hay credenciales en
     ningún target).

Para investigar un target DOWN: el campo `ultimo_error` es el mismo que muestra Status > Targets.
  - "connection refused"     -> el exporter o la API no está escuchando (¿contenedor/API detenidos?)
  - "context deadline exceeded" -> responde más lento que scrape_timeout (4 s)
  - "no such host"           -> el exporter no está en la red hito-10-api_default
Uso: python scripts/verificar_targets.py [--guardar]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROM = "http://127.0.0.1:9090"
RAIZ = Path(__file__).resolve().parent.parent


def consulta(expr: str) -> list:
    return httpx.get(f"{PROM}/api/v1/query", params={"query": expr}, timeout=5).json()["data"]["result"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guardar", action="store_true")
    args = ap.parse_args()
    try:
        targets = httpx.get(f"{PROM}/api/v1/targets", timeout=5).json()["data"]["activeTargets"]
    except httpx.HTTPError as e:
        sys.exit(f"Prometheus no responde en {PROM}: {type(e).__name__}")
    filas = []
    for t in sorted(targets, key=lambda t: (t["labels"]["job"], t["labels"].get("instance", ""))):
        filas.append({"job": t["labels"]["job"], "componente": t["labels"].get("componente", "-"),
                      "instance": t["labels"]["instance"], "estado": t["health"],
                      "ultimo_scrape_s": round(t.get("lastScrapeDuration", 0), 3),
                      "ultimo_error": t.get("lastError") or ""})
    print(f"{'job':12} {'componente':11} {'estado':7} {'scrape':>8}  instance / error")
    for f in filas:
        print(f"{f['job']:12} {f['componente']:11} {f['estado']:7} {f['ultimo_scrape_s']:>7}s  "
              f"{f['instance']} {f['ultimo_error'][:70]}")

    api = {r["metric"]["base"]: r["value"][1] for r in consulta("fixture2030_dependencia_up")}
    tcp = {r["metric"]["componente"]: r["value"][1] for r in consulta('probe_success{job="sonda_tcp"}')}
    print("\nbase        API(dependencia_up)  sonda TCP")
    bases = {}
    for nombre in ["MongoDB", "Neo4j", "Cassandra", "Redis", "InfluxDB", "IRIS"]:
        a, s = api.get(nombre, "sin dato"), tcp.get(nombre.lower(), "sin dato")
        bases[nombre] = {"dependencia_up": a, "probe_success": s}
        print(f"{nombre:11} {a:20} {s}")
    caidos = [f for f in filas if f["estado"] != "up"]
    print(f"\n{len(filas) - len(caidos)}/{len(filas)} targets UP")
    if args.guardar:
        destino = RAIZ / "evidencia" / "prometheus_targets.json"
        destino.parent.mkdir(exist_ok=True)
        destino.write_text(json.dumps({"consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                       "targets": filas, "bases": bases}, indent=2, ensure_ascii=False),
                           encoding="utf-8")
        print(f"Guardado en {destino.relative_to(RAIZ)}")
    sys.exit(1 if caidos else 0)


if __name__ == "__main__":
    main()
