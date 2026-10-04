#!/usr/bin/env python3
"""Carga por lotes (line protocol -> POST /api/v3/write_lp) — Fixture 2030, Hito 8.

SOLO carga: lee los archivos generados por generacion_puntos.py; no genera ni valida.

Estrategia (ver docs/carga_de_datos.md):
  * lotes de --lote líneas (default 5.000) y como máximo --max-bytes por request;
  * --hilos requests concurrentes (default 4) con cola acotada (memoria constante);
  * cada partido se carga en orden temporal; los partidos se cargan en paralelo;
    al final se cargan los eventos tardíos (tardios.lp.gz);
  * reintentos con backoff exponencial + jitter ante errores de red, 429 y 5xx;
  * un 400 NO se reintenta: se registran las líneas rechazadas (accept_partial=true);
  * 401/403 abortan la carga (token inválido);
  * métricas: puntos enviados/aceptados/rechazados, latencias de lote y puntos/s.

Uso:
    python3 scripts/carga_lotes.py                     # última corrida generada
    python3 scripts/carga_lotes.py --lote 10000 --hilos 8
    python3 scripts/carga_lotes.py --archivo data/muestras/errores_demo.lp
"""
from __future__ import annotations

import argparse
import gzip
import json
import platform
import random
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import influx_comun as ic  # noqa: E402


class Metricas:
    def __init__(self):
        self.lock = threading.Lock()
        self.enviadas = 0
        self.rechazadas = 0
        self.lotes = 0
        self.lotes_fallidos = 0
        self.reintentos = 0
        self.lat_ms: list[float] = []
        self.muestras_error: list[dict] = []
        self.abortar: str | None = None


def abrir(ruta: Path):
    return gzip.open(ruta, "rt", encoding="utf-8") if ruta.suffix == ".gz" else open(ruta, encoding="utf-8")


def lotes_de(ruta: Path, tam: int, max_bytes: int):
    buf, nbytes = [], 0
    with abrir(ruta) as f:
        for ln in f:
            if not ln.strip() or ln.startswith("#"):
                continue
            b = len(ln.encode("utf-8"))
            if buf and (len(buf) >= tam or nbytes + b > max_bytes):
                yield "".join(buf), len(buf)
                buf, nbytes = [], 0
            buf.append(ln if ln.endswith("\n") else ln + "\n")
            nbytes += b
    if buf:
        yield "".join(buf), len(buf)


def enviar(m: Metricas, db: str, cuerpo: str, n: int, reintentos: int):
    if m.abortar:
        return
    espera = 0.5
    for intento in range(reintentos + 1):
        t0 = time.perf_counter()
        try:
            r = ic.escribir_lp(db, cuerpo)
            dt = (time.perf_counter() - t0) * 1000
            with m.lock:
                m.lotes += 1
                m.enviadas += n
                m.lat_ms.append(dt)
                if not r["ok"]:
                    m.rechazadas += len(r["rechazadas"])
                    for d in r["rechazadas"][: max(0, 10 - len(m.muestras_error))]:
                        m.muestras_error.append(d)
            return
        except ic.ErrorHTTP as e:
            if e.status in (401, 403):
                m.abortar = f"HTTP {e.status}: token inválido o sin permisos ({e.cuerpo[:200]})"
                return
            if e.status not in (408, 429) and e.status < 500:
                with m.lock:
                    m.lotes_fallidos += 1
                    m.muestras_error.append({"error_message": str(e)[:300]})
                return
            err = e
        except Exception as e:  # red, timeout, conexión rechazada
            err = e
        if intento < reintentos:
            with m.lock:
                m.reintentos += 1
            time.sleep(espera + random.uniform(0, espera))
            espera = min(espera * 2, 15)
    with m.lock:
        m.lotes_fallidos += 1
        m.muestras_error.append({"error_message": f"lote descartado tras {reintentos} reintentos: {err}"[:300]})


def cargar_archivos(archivos: list[Path], db: str, tam: int, hilos: int, max_bytes: int,
                    reintentos: int, m: Metricas, progreso: bool = True):
    """Intercala lotes de todos los archivos (partidos en paralelo, cada uno en orden)."""
    generadores = [lotes_de(a, tam, max_bytes) for a in archivos]
    pendientes = set()
    ultimo = time.perf_counter()
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        while generadores and not m.abortar:
            for g in list(generadores):
                try:
                    cuerpo, n = next(g)
                except StopIteration:
                    generadores.remove(g)
                    continue
                pendientes.add(ex.submit(enviar, m, db, cuerpo, n, reintentos))
                if len(pendientes) >= hilos * 2:            # cola acotada
                    _, pendientes = wait(pendientes, return_when=FIRST_COMPLETED)
            if progreso and time.perf_counter() - ultimo > 2:
                ultimo = time.perf_counter()
                print(f"  ... {m.enviadas:,} puntos enviados", flush=True)
        wait(pendientes)


def demo_errores(db: str):
    """Muestra qué pasa con un lote que mezcla líneas válidas e inválidas (accept_partial=true)."""
    import time as _t
    ts = int(_t.time() * 1000)
    lineas = [
        f"prueba_errores,origen=demo valor=1.5 {ts}",           # válida: crea valor como Float64
        f"prueba_errores,origen=demo valor=7i {ts + 1}",        # conflicto de tipo (Int64 vs Float64)
        f"prueba_errores,origen=demo valor=2.5 {ts + 2}",       # válida
        "esto no es line protocol",                             # error de sintaxis
        f'prueba_errores,origen=demo valor="texto" {ts + 3}',   # conflicto de tipo (Utf8)
    ]
    print("Lote enviado:")
    for i, ln in enumerate(lineas, 1):
        print(f"  {i}: {ln}")
    r = ic.escribir_lp(db, "\n".join(lineas) + "\n")
    if r["ok"]:
        print("El servidor aceptó todas las líneas (inesperado).")
        return
    print(f"\nRespuesta: {r.get('error', '')}")
    print(f"Líneas rechazadas: {len(r['rechazadas'])} de {len(lineas)} (las válidas se escribieron)")
    for d in r["rechazadas"]:
        print(f"  - línea {d.get('line_number')}: {d.get('error_message')}")
    print("Decisión del cargador: un 400 no se reintenta (el dato es inválido, reintentar no lo corrige);")
    print("las líneas rechazadas se registran en la evidencia para corregir la fuente.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corrida", help="nombre/directorio de la corrida (default: la última)")
    ap.add_argument("--archivo", action="append", help="cargar este archivo .lp/.lp.gz en vez de una corrida")
    ap.add_argument("--db", default=ic.DB_VIVO)
    ap.add_argument("--lote", type=int, default=5000)
    ap.add_argument("--hilos", type=int, default=4)
    ap.add_argument("--max-bytes", type=int, default=8 * 1024 * 1024)
    ap.add_argument("--reintentos", type=int, default=5)
    ap.add_argument("--sin-tardios", action="store_true")
    ap.add_argument("--etiqueta", default="", help="texto libre para identificar la medición")
    ap.add_argument("--demo-errores", action="store_true",
                    help="envía un lote chico con líneas inválidas para mostrar el manejo de errores")
    a = ap.parse_args()

    if a.demo_errores:
        demo_errores(a.db)
        return

    if a.archivo:
        archivos, tardios, man = [Path(x) for x in a.archivo], [], None
    else:
        d = ic.dir_corrida(a.corrida)
        man = ic.cargar_manifiesto(str(d))
        archivos = [d / p["archivo"] for p in man["partidos"]]
        tardios = [] if a.sin_tardios else [d / "tardios.lp.gz"]

    print(f"Destino: {ic.URL}  db={a.db}  precision={ic.PRECISION_LP}")
    print(f"Lote={a.lote} líneas  hilos={a.hilos}  reintentos={a.reintentos}")
    print(f"Archivos: {len(archivos)} + {len(tardios)} tardío(s)")
    m = Metricas()
    t0 = time.perf_counter()
    cargar_archivos(archivos, a.db, a.lote, a.hilos, a.max_bytes, a.reintentos, m)
    t_principal = time.perf_counter() - t0
    if tardios and not m.abortar:
        print("Cargando eventos tardíos (llegan después del resto del partido)...")
        cargar_archivos(tardios, a.db, a.lote, a.hilos, a.max_bytes, a.reintentos, m, progreso=False)
    total_s = time.perf_counter() - t0

    if m.abortar:
        print("ABORTADO:", m.abortar)
        sys.exit(2)

    lat = sorted(m.lat_ms) or [0.0]
    res = {
        "fecha_utc": ic.ahora_iso(),
        "etiqueta": a.etiqueta,
        "url": ic.URL,
        "db": a.db,
        "corrida": man["corrida"] if man else None,
        "puntos_esperados": man["total_puntos"] if man else None,
        "precision": ic.PRECISION_LP,
        "lote": a.lote,
        "hilos": a.hilos,
        "lotes_ok": m.lotes,
        "lotes_fallidos": m.lotes_fallidos,
        "reintentos": m.reintentos,
        "puntos_enviados": m.enviadas,
        "lineas_rechazadas": m.rechazadas,
        "puntos_aceptados": m.enviadas - m.rechazadas,
        "segundos_total": round(total_s, 3),
        "segundos_sin_tardios": round(t_principal, 3),
        "puntos_por_segundo": round((m.enviadas - m.rechazadas) / max(total_s, 1e-9), 1),
        "latencia_lote_ms": {"p50": round(statistics.median(lat), 1),
                             "p95": round(lat[int(0.95 * (len(lat) - 1))], 1),
                             "max": round(lat[-1], 1)},
        "cliente": {"python": platform.python_version(), "so": platform.platform()},
        "muestras_error": m.muestras_error,
    }
    print(json.dumps({k: v for k, v in res.items() if k != "muestras_error"}, indent=1, ensure_ascii=False))
    if m.muestras_error:
        print("Primeros errores / líneas rechazadas:")
        for e in m.muestras_error[:10]:
            print("  -", json.dumps(e, ensure_ascii=False)[:300])
    ic.DIR_EVIDENCIA.mkdir(parents=True, exist_ok=True)
    out = ic.DIR_EVIDENCIA / f"carga_{ic.sello()}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Métricas guardadas en {out.relative_to(ic.RAIZ)}")
    if m.lotes_fallidos:
        sys.exit(1)


if __name__ == "__main__":
    main()
