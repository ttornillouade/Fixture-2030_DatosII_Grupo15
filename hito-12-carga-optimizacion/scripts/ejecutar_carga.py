"""CARGA Y MEDICIÓN: generador de carga del flujo "comentarios en vivo durante un partido".

Modelo cerrado (usuarios virtuales, VU): cada VU repite elegir operación -> request -> pausa (think time).
Etapas: calentamiento -> rampa -> sostenimiento. Las métricas del informe se calculan SOLO sobre el
sostenimiento; el CSV crudo guarda todas las requests con su etapa.

Operaciones (proporción configurable en config/escenario.json):
  feed_vivo      GET  /partidos/{P}/comentarios?bucket=<ventana actual>&limit=20   (clave caliente)
  feed_historial GET  /partidos/{P}/comentarios?bucket=<ventana precargada>&limit=20
  publicar       POST /partidos/{P}/comentarios                                    (escritura)

Los VU se reparten en `procesos_generador` procesos de Python: con uno solo, el generador saturaba
un núcleo antes que la API (corrida exploratoria, ver docs/linea_base.md).

Mide además, cada 2 s (hilo aparte): CPU de los procesos del generador, CPU y memoria del proceso de
la API, CPU y memoria de cada contenedor (docker stats) y CPU/memoria total del sistema operativo (RF6).

Interrupción segura: Ctrl+C (guarda lo medido) o corte automático si más de `max_errores_pct` de las
últimas 100 requests de un proceso fallan.

Uso: python scripts/ejecutar_carga.py --etiqueta linea_base [--escenario config/escenario.json] [--api-pid PID]
"""
import argparse
import asyncio
import csv
import json
import multiprocessing as mp
import platform
import random
import statistics
import subprocess
import threading
import time
from pathlib import Path

import httpx
import psutil

import comun


# --- Medición de recursos ----------------------------------------------------------------------------
class Recursos(threading.Thread):
    def __init__(self, ruta: Path, api_pid: int | None, t0: float, generadores: list[int]):
        super().__init__(daemon=True)
        self.ruta, self.t0, self.fin = ruta, t0, threading.Event()
        self.gen = [psutil.Process(p) for p in generadores]
        self.api = psutil.Process(api_pid) if api_pid else None
        self.filas = []

    def _api_procs(self):
        if not self.api:
            return []
        try:
            return [self.api] + self.api.children(recursive=True)
        except psutil.Error:
            return []

    @staticmethod
    def _cpu(p):
        try:
            return p.cpu_percent(None)
        except psutil.Error:
            return 0.0

    def run(self):
        psutil.cpu_percent(None)
        for p in self.gen + self._api_procs():
            self._cpu(p)
        while not self.fin.wait(2.0):
            t = round(time.perf_counter() - self.t0, 1)
            fila = {"t": t, "so_cpu_pct": psutil.cpu_percent(None), "so_mem_pct": psutil.virtual_memory().percent,
                    "generador_cpu_pct": round(sum(self._cpu(p) for p in self.gen), 1)}
            procs = self._api_procs()
            if procs:
                fila["api_cpu_pct"] = round(sum(self._cpu(p) for p in procs), 1)
                fila["api_mem_mb"] = round(sum(p.memory_info().rss for p in procs) / 2**20, 1)
                fila["api_procesos"] = len(procs)
            r = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}};{{.CPUPerc}};{{.MemUsage}}"],
                               capture_output=True, text=True)
            for linea in r.stdout.splitlines():
                nombre, cpu, mem = linea.split(";")
                corto = nombre.replace("fixture2030-", "")
                fila[f"{corto}_cpu_pct"] = cpu.rstrip("%")
                fila[f"{corto}_mem"] = mem.split("/")[0].strip()
            self.filas.append(fila)
        claves = sorted({k for f in self.filas for k in f}, key=lambda k: (k != "t", k))
        with self.ruta.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=claves)
            w.writeheader()
            w.writerows(self.filas)


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return float("nan")
    v = sorted(valores)
    k = (len(v) - 1) * p / 100
    i = int(k)
    return v[i] if i + 1 >= len(v) else v[i] + (v[i + 1] - v[i]) * (k - i)


# --- Generación (corre dentro de cada proceso) --------------------------------------------------------
async def _vus(idx: int, procesos: int, esc: dict, etiqueta: str, epoch: float, historial: list, parar) -> tuple:
    """Corre los VU idx, idx+procesos, idx+2*procesos, ... con un cliente HTTP propio del proceso."""
    rnd = random.Random(esc["semilla"] * 100 + idx)
    cal, rampa, sost = esc["calentamiento_s"], esc["rampa_s"], esc["sostenimiento_s"]
    total = cal + rampa + sost
    vu_max, vu_cal = esc["usuarios_virtuales"], esc["usuarios_calentamiento"]
    ops, pesos = zip(*esc["proporcion"].items())
    partidos, pesos_partido = zip(*esc["partidos"].items())
    mios = list(range(idx, vu_max, procesos))
    registros, creados, enviados = [], [], [0]

    def etapa(t):
        return "calentamiento" if t < cal else "rampa" if t < cal + rampa else "sostenimiento"

    def vus_objetivo(t):
        if t < cal:
            return vu_cal
        if t < cal + rampa:
            return vu_cal + int((vu_max - vu_cal) * (t - cal) / rampa)
        return vu_max

    limites = httpx.Limits(max_connections=len(mios) + 5, max_keepalive_connections=len(mios) + 5)
    async with httpx.AsyncClient(base_url=comun.API_URL, timeout=esc["timeout_cliente_s"], limits=limites) as cli:

        async def una_operacion(op: str):
            partido = rnd.choices(partidos, weights=pesos_partido)[0]
            if op == "publicar":
                enviados[0] += 1
                return await cli.post(f"/partidos/{partido}/comentarios",
                                      json={"usuarioId": comun.usuario(rnd.randrange(10_000)),
                                            "texto": f"carga {etiqueta} {idx}-{enviados[0]}"})
            if op == "feed_vivo":
                bucket = comun.bucket_de(comun.ahora()).strftime("%Y-%m-%dT%H:%M:%SZ")
                return await cli.get(f"/partidos/{partido}/comentarios", params={"bucket": bucket, "limit": 20})
            p, b = rnd.choice(historial).split("|")
            return await cli.get(f"/partidos/{p}/comentarios", params={"bucket": b.replace("+00:00", "Z"), "limit": 20})

        async def vu(n: int):
            while not parar.is_set():
                t = time.time() - epoch
                if t >= total:
                    return
                if t < 0 or n >= vus_objetivo(t):   # todavía no empezó o este VU no entró en la rampa
                    await asyncio.sleep(0.2)
                    continue
                op = rnd.choices(ops, weights=pesos)[0]
                inicio = time.perf_counter()
                status, error = 0, ""
                try:
                    r = await una_operacion(op)
                    status = r.status_code
                    if status == 201:
                        c = r.json()
                        creados.append(";".join([c["comentarioId"], c["partidoCodigo"], c["usuarioId"], c["creadoEn"],
                                                 c["texto"]]))
                    if status >= 400:
                        error = r.json().get("code", f"HTTP{status}")
                except httpx.TimeoutException:
                    error = "TIMEOUT_CLIENTE"
                except httpx.HTTPError as e:
                    error = type(e).__name__
                except ValueError:
                    error = "RESPUESTA_NO_JSON"
                ms = (time.perf_counter() - inicio) * 1000
                registros.append((round(t, 3), etapa(t), op, status, round(ms, 2), error))
                if len(registros) >= 100 and len(registros) % 25 == 0:
                    malos = sum(1 for x in registros[-100:] if x[5])
                    if malos > esc["max_errores_pct"]:
                        print(f"Interrupción segura (proceso {idx}): {malos}/100 errores en las últimas requests")
                        parar.set()
                await asyncio.sleep(rnd.uniform(*esc["think_time_s"]))

        await asyncio.gather(*(vu(n) for n in mios))
    return registros, creados, enviados[0]


def _proceso(idx, procesos, esc, etiqueta, epoch, historial, parar, cola):
    try:
        cola.put((idx, asyncio.run(_vus(idx, procesos, esc, etiqueta, epoch, historial, parar))))
    except KeyboardInterrupt:
        cola.put((idx, ([], [], 0)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escenario", default=str(comun.RAIZ / "config" / "escenario.json"))
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--api-pid", type=int, default=None, help="PID de uvicorn, para medir su CPU y memoria")
    args = ap.parse_args()
    esc = json.loads(Path(args.escenario).read_text(encoding="utf-8"))
    manifiesto = json.loads((comun.EVIDENCIA / "datos_preparados.json").read_text(encoding="utf-8"))
    historial = list(manifiesto["por_bucket_partido"])  # "P901|<bucket>": ventanas precargadas

    marca = comun.ahora().strftime("%Y%m%dT%H%M%SZ")
    salida = comun.EVIDENCIA / f"{args.etiqueta}_{marca}"
    salida.mkdir(parents=True, exist_ok=True)
    cal, rampa, sost = esc["calentamiento_s"], esc["rampa_s"], esc["sostenimiento_s"]
    ops = list(esc["proporcion"])
    procesos = esc.get("procesos_generador", 1)

    parar, cola = mp.Event(), mp.Queue()
    epoch = time.time() + 2.0                      # inicio común para todos los procesos
    hijos = [mp.Process(target=_proceso, args=(i, procesos, esc, args.etiqueta, epoch, historial, parar, cola))
             for i in range(procesos)]
    for h in hijos:
        h.start()
    recursos = Recursos(salida / "recursos.csv", args.api_pid, time.perf_counter() + (epoch - time.time()),
                        [h.pid for h in hijos])
    recursos.start()
    registros, creados, enviados = [], [], 0
    try:
        for _ in hijos:
            _, (r, c, e) = cola.get()
            registros += r
            creados += c
            enviados += e
    except KeyboardInterrupt:
        parar.set()
        print("Interrumpida por el usuario: se guardan los resultados recibidos")
    for h in hijos:
        h.join(timeout=15)
    recursos.fin.set()
    recursos.join()
    registros.sort()

    # --- Resultados ---------------------------------------------------------------------------------
    with (salida / "requests.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "etapa", "operacion", "status", "latencia_ms", "error"])
        w.writerows(registros)
    (salida / "ids_creados.txt").write_text("\n".join(creados), encoding="utf-8")

    medidos = [r for r in registros if r[1] == "sostenimiento"]

    def resumen(filas):
        lat = [r[4] for r in filas]
        ok = [r for r in filas if 200 <= r[3] < 300]
        errs = {}
        for r in filas:
            if r[5]:
                errs[r[5]] = errs.get(r[5], 0) + 1
        return {"requests": len(filas), "exitosas": len(ok), "errores": len(filas) - len(ok),
                "tasa_error_pct": round(100 * (len(filas) - len(ok)) / len(filas), 3) if filas else None,
                "errores_por_tipo": errs, "throughput_rps": round(len(filas) / sost, 1),
                "latencia_ms": {"min": round(min(lat), 2) if lat else None,
                                "media": round(statistics.fmean(lat), 2) if lat else None,
                                "p50": round(percentil(lat, 50), 2), "p90": round(percentil(lat, 90), 2),
                                "p95": round(percentil(lat, 95), 2), "p99": round(percentil(lat, 99), 2),
                                "max": round(max(lat), 2) if lat else None}}

    sost_rec = [f for f in recursos.filas if f["t"] >= cal + rampa]

    def media(clave):
        vals = [float(f[clave]) for f in sost_rec if f.get(clave) not in (None, "")]
        return round(statistics.fmean(vals), 1) if vals else None

    informe = {
        "etiqueta": args.etiqueta, "inicio_utc": marca, "commit": comun.commit_actual(),
        "escenario": esc, "api_url": comun.API_URL, "versiones": comun.versiones_imagenes(),
        "entorno": {"cpu_logicos": psutil.cpu_count(), "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
                    "so": platform.platform(), "python": platform.python_version()},
        "medicion": "latencia = tiempo de respuesta HTTP completo visto por el generador (perf_counter, ms); "
                    "throughput = requests completadas en el sostenimiento / duración del sostenimiento (req/s); "
                    "CPU en % de un núcleo (100 = 1 núcleo), media de muestras cada 2 s",
        "global": resumen(medidos),
        "por_operacion": {op: resumen([r for r in medidos if r[2] == op]) for op in ops},
        "escrituras": {"enviadas_total": enviados, "201_total": len(creados)},
        "recursos_sostenimiento_media": {k: media(k) for k in
                                         ["so_cpu_pct", "generador_cpu_pct", "api_cpu_pct", "api_mem_mb",
                                          "cassandra_cpu_pct", "redis_cpu_pct"]},
        "interrumpida": parar.is_set(), "procesos_generador": procesos,
    }
    comun.guardar_json(salida / "resumen.json", informe)
    g = informe["global"]
    print(f"[{args.etiqueta}] sostenimiento {sost}s, {esc['usuarios_virtuales']} VU: {g['requests']} req, "
          f"{g['throughput_rps']} req/s, p50={g['latencia_ms']['p50']} p95={g['latencia_ms']['p95']} "
          f"p99={g['latencia_ms']['p99']} ms, errores={g['tasa_error_pct']}%")
    print(f"Recursos (media): {informe['recursos_sostenimiento_media']}")
    print(f"Resultados en {salida.relative_to(comun.RAIZ)}")
    (comun.EVIDENCIA / f"ultima_{args.etiqueta}.txt").write_text(salida.name, encoding="utf-8")


if __name__ == "__main__":
    main()
