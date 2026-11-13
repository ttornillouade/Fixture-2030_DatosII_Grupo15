"""Prueba de falla controlada con evidencia en Prometheus y Grafana (RF10).

Secuencia (todo sobre contenedores y datos de laboratorio, sin borrar volúmenes: RNF11):
  1. tráfico liviano y constante contra la API (~12 req/s: comentarios -> Cassandra, equipos -> MongoDB,
     sesión -> Redis), durante toda la prueba;
  2. NORMAL      `--normal` segundos;
  3. FALLA       `docker stop` del contenedor elegido (por defecto fixture2030-cassandra);
  4. CAÍDA       `--caida` segundos con la base detenida;
  5. RECUPERACIÓN `docker start` + espera del healthcheck, y `--post` segundos de observación.
Al final consulta Prometheus (query_range) y guarda en evidencia/prueba_de_falla_<marca>/:
  eventos.json (línea de tiempo), series.csv, alertas.json (alertas activas durante la caída),
  trafico.json (lo que vio el cliente), prueba_de_falla.png (gráfico) y, si hay Microsoft Edge o
  Chrome, capturas del dashboard de Grafana durante la caída y después.

Uso: python scripts/ejecutar_prueba_controlada.py [--base cassandra] [--normal 60] [--caida 60] [--post 90]
"""
import argparse
import csv
import json
import os
import random
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROM = "http://127.0.0.1:9090"
API = "http://127.0.0.1:8000"
GRAFANA = "http://localhost:3000"
RAIZ = Path(__file__).resolve().parent.parent
FUENTE = {"cassandra": "Cassandra", "mongodb": "MongoDB", "redis": "Redis", "neo4j": "Neo4j",
          "influxdb": "InfluxDB", "iris": "IRIS"}


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Trafico:
    """Cliente de prueba: un hilo independiente por base (~4 req/s cada uno), para que una base lenta no
    frene en el cliente las requests de las otras (si fuera un solo hilo, la caída de Cassandra se vería
    también como una caída del tráfico de MongoDB y Redis, y sería un artefacto del cliente)."""
    def __init__(self):
        self.fin = threading.Event()
        self.conteo: dict[str, dict[str, int]] = {}
        self.latencias: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self.hilos = [threading.Thread(target=self._hilo, args=(b, i), daemon=True)
                      for i, b in enumerate(["Cassandra", "MongoDB", "Redis"])]

    @staticmethod
    def _ruta(base, rnd):
        bucket = ahora().replace(minute=ahora().minute // 5 * 5, second=0, microsecond=0)
        if base == "Cassandra":
            return f"/partidos/{rnd.choice(['P901', 'P902'])}/comentarios?bucket={bucket:%Y-%m-%dT%H:%M:%SZ}&limit=20"
        if base == "MongoDB":
            return rnd.choice(["/equipos/E010", "/jugadores?equipoCodigo=E010&limit=5"])
        return "/sesiones/s-demo-001"

    def _hilo(self, base, semilla):
        rnd = random.Random(13 + semilla)
        with httpx.Client(base_url=API, timeout=10) as cli:
            while not self.fin.is_set():
                inicio = time.perf_counter()
                try:
                    status = str(cli.get(self._ruta(base, rnd)).status_code)
                except httpx.HTTPError as e:
                    status = type(e).__name__
                with self._lock:
                    self.conteo.setdefault(base, {}).setdefault(status, 0)
                    self.conteo[base][status] += 1
                    self.latencias.setdefault(base, []).append(time.perf_counter() - inicio)
                time.sleep(rnd.uniform(0.2, 0.3))

    def start(self):
        for h in self.hilos:
            h.start()

    def join(self):
        for h in self.hilos:
            h.join(timeout=15)

    def resumen(self):
        salida = {}
        for base, lat in self.latencias.items():
            lat = sorted(lat)
            salida[base] = {"requests": len(lat), "por_status": self.conteo.get(base, {}),
                            "latencia_cliente_p50_s": round(lat[len(lat) // 2], 3),
                            "latencia_cliente_max_s": round(lat[-1], 3)}
        return salida


def docker(*args) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True).stdout.strip()


def esperar_sana(contenedor: str, limite_s: int = 240) -> float:
    inicio = time.time()
    while time.time() - inicio < limite_s:
        if docker("inspect", "-f", "{{.State.Health.Status}}", contenedor) == "healthy":
            return time.time() - inicio
        time.sleep(2)
    return -1


def capturar(nombre: str, desde: datetime, hasta: datetime, carpeta: Path) -> str:
    """Captura del dashboard con un navegador headless (Edge o Chrome). Devuelve el archivo o el motivo."""
    candidatos = [os.environ.get("NAVEGADOR", ""), shutil.which("msedge") or "", shutil.which("chrome") or "",
                  r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("chromium") or ""]
    nav = next((c for c in candidatos if c and Path(c).exists()), None)
    if not nav:
        return "sin navegador headless: capturar a mano desde Grafana"
    url = (f"{GRAFANA}/d/fixture2030?orgId=1&kiosk&refresh=&from={int(desde.timestamp() * 1000)}"
           f"&to={int(hasta.timestamp() * 1000)}")
    destino = carpeta / f"{nombre}.png"
    perfil = carpeta / ".perfil_navegador"
    subprocess.run([nav, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={perfil}",
                    "--window-size=1600,2000", "--virtual-time-budget=20000", f"--screenshot={destino}", url],
                   capture_output=True, timeout=120)
    shutil.rmtree(perfil, ignore_errors=True)
    return destino.name if destino.exists() else "la captura falló"


def rango(expr: str, desde: datetime, hasta: datetime) -> list:
    r = httpx.get(f"{PROM}/api/v1/query_range", params={"query": expr, "start": desde.timestamp(),
                                                         "end": hasta.timestamp(), "step": "5s"}, timeout=10)
    return r.json()["data"]["result"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="cassandra", choices=list(FUENTE))
    ap.add_argument("--normal", type=int, default=60)
    ap.add_argument("--caida", type=int, default=60)
    ap.add_argument("--post", type=int, default=90)
    args = ap.parse_args()
    contenedor, fuente = f"fixture2030-{args.base}", FUENTE[args.base]
    httpx.get(f"{PROM}/-/ready", timeout=3).raise_for_status()
    httpx.get(f"{API}/salud", timeout=3).raise_for_status()

    marca = ahora().strftime("%Y%m%dT%H%M%SZ")
    carpeta = RAIZ / "evidencia" / f"prueba_de_falla_{args.base}_{marca}"
    carpeta.mkdir(parents=True)
    eventos = []

    def evento(nombre, **extra):
        eventos.append({"utc": ahora().isoformat(timespec="seconds"), "evento": nombre, **extra})
        print(f"{eventos[-1]['utc']}  {nombre} {extra or ''}")

    trafico = Trafico()
    trafico.start()
    evento("inicio_trafico")
    time.sleep(args.normal)

    evento("docker_stop", contenedor=contenedor)
    docker("stop", contenedor)
    salud, alertas, alertas_fin = {}, [], []
    try:  # pase lo que pase durante la caída, la base se vuelve a iniciar (RNF11)
        time.sleep(args.caida / 2)
        alertas = httpx.get(f"{PROM}/api/v1/alerts", timeout=5).json()["data"]["alerts"]
        inicio = time.perf_counter()
        try:
            salud = httpx.get(f"{API}/salud/dependencias", timeout=60).json()
        except httpx.HTTPError as e:
            salud = {"estado": f"sin respuesta ({type(e).__name__})"}
        salud["segundos_de_respuesta"] = round(time.perf_counter() - inicio, 2)
        evento("diagnostico_durante_la_caida", api_salud=salud["estado"], segundos=salud["segundos_de_respuesta"])
        time.sleep(max(0, args.caida / 2 - salud["segundos_de_respuesta"]))
        alertas_fin = httpx.get(f"{PROM}/api/v1/alerts", timeout=5).json()["data"]["alerts"]
        evento("alertas_al_final_de_la_caida", activas=[a["labels"]["alertname"] for a in alertas_fin
                                                        if a["state"] == "firing"])
    finally:
        evento("docker_start", contenedor=contenedor)
        docker("start", contenedor)
    sana = esperar_sana(contenedor)
    evento("contenedor_healthy", segundos_hasta_healthy=round(sana, 1))
    time.sleep(args.post)
    trafico.fin.set()
    trafico.join()
    evento("fin_trafico")
    time.sleep(6)  # un scrape más

    desde = datetime.fromisoformat(eventos[0]["utc"])
    hasta = ahora()
    consultas = {
        "dependencia_up": f'fixture2030_dependencia_up{{base="{fuente}"}}',
        "sonda_tcp": f'probe_success{{job="sonda_tcp",componente="{args.base}"}}',
        "req_s_ok": f'sum(rate(fixture2030_http_requests_total{{fuente="{fuente}",status=~"2.."}}[30s]))',
        "req_s_5xx": f'sum(rate(fixture2030_http_requests_total{{fuente="{fuente}",status=~"5.."}}[30s]))',
        "p95_s": f'histogram_quantile(0.95, sum by (le) (rate(fixture2030_http_request_duration_seconds_bucket{{fuente="{fuente}"}}[30s])))',
        "req_s_ok_MongoDB": 'sum(rate(fixture2030_http_requests_total{fuente="MongoDB",status=~"2.."}[30s]))',
        "req_s_ok_Redis": 'sum(rate(fixture2030_http_requests_total{fuente="Redis",status=~"2.."}[30s]))',
    }
    series = {}
    for nombre, expr in consultas.items():
        res = rango(expr, desde, hasta)
        series[nombre] = {float(t): float(v) for t, v in res[0]["values"]} if res else {}
    tiempos = sorted({t for s in series.values() for t in s})
    with (carpeta / "series.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["utc"] + list(consultas))
        for t in tiempos:
            w.writerow([datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")] +
                       [series[n].get(t, "") for n in consultas])

    def resumir(lista):
        return [{"alerta": a["labels"]["alertname"], "estado": a["state"], "desde": a.get("activeAt"),
                 "labels": {k: v for k, v in a["labels"].items() if k != "alertname"}} for a in lista]

    (carpeta / "alertas.json").write_text(json.dumps({"a_mitad_de_la_caida": resumir(alertas),
                                                      "al_final_de_la_caida": resumir(alertas_fin)},
                                                     indent=2, ensure_ascii=False), encoding="utf-8")
    (carpeta / "trafico.json").write_text(json.dumps(trafico.resumen(), indent=2), encoding="utf-8")
    (carpeta / "eventos.json").write_text(json.dumps({"consultas_promql": consultas, "eventos": eventos,
                                                      "diagnostico_api_durante_la_caida": salud},
                                                     indent=2, ensure_ascii=False), encoding="utf-8")
    grafico(series, eventos, carpeta / "prueba_de_falla.png", fuente)
    cap = capturar("grafana_prueba_completa", desde, hasta, carpeta)
    print(f"Captura de Grafana: {cap}")
    print(f"Evidencia en {carpeta.relative_to(RAIZ)}")


def grafico(series, eventos, destino, fuente):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter

    def xy(nombre):
        s = series.get(nombre, {})
        return [datetime.fromtimestamp(t, timezone.utc) for t in sorted(s)], [s[t] for t in sorted(s)]

    fig, ejes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    ejes[0].step(*xy("dependencia_up"), where="post", label=f"{fuente}: fixture2030_dependencia_up (API)")
    ejes[0].step(*xy("sonda_tcp"), where="post", linestyle="--", label="probe_success (sonda TCP)")
    ejes[0].set_ylim(-0.1, 1.2)
    ejes[0].set_ylabel("1 = arriba")
    ejes[1].plot(*xy("req_s_ok"), label=f"{fuente} 2xx")
    ejes[1].plot(*xy("req_s_5xx"), label=f"{fuente} 5xx", color="tab:red")
    ejes[1].plot(*xy("req_s_ok_MongoDB"), label="MongoDB 2xx", color="tab:green", alpha=.6)
    ejes[1].plot(*xy("req_s_ok_Redis"), label="Redis 2xx", color="tab:purple", alpha=.6)
    ejes[1].set_ylabel("req/s (rate 30 s)")
    ejes[2].plot(*xy("p95_s"), label=f"p95 {fuente} dentro de la API")
    ejes[2].set_ylabel("segundos")
    for e in eventos:
        if e["evento"] in ("docker_stop", "docker_start", "contenedor_healthy"):
            t = datetime.fromisoformat(e["utc"])
            for ax in ejes:
                ax.axvline(t, color="gray", linestyle=":")
            ejes[0].annotate(e["evento"], (t, 1.1), fontsize=8, rotation=0)
    for ax in ejes:
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=.3)
    ejes[2].xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
    ejes[2].set_xlabel("hora UTC")
    fig.suptitle(f"Prueba de falla controlada: {fuente} detenida (datos de Prometheus, paso 5 s)")
    fig.tight_layout()
    fig.savefig(destino, dpi=110)


if __name__ == "__main__":
    main()
