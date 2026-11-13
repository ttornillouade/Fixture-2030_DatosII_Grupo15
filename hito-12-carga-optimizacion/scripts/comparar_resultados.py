"""COMPARACIÓN antes/después (RF10): tablas y gráficos a partir de las corridas guardadas en docs/evidencia/.

Agrupa las corridas por configuración (prefijo de la etiqueta, sin el _rN de la repetición) y para cada
una informa la mediana entre repeticiones y el rango (mín-máx). Genera:
  docs/evidencia/comparacion.md               tabla de latencia, throughput, errores, recursos e integridad
  docs/evidencia/comparacion_latencias.png    p50/p95/p99 por configuración (barras = mediana, línea = rango)
  docs/evidencia/comparacion_distribucion.png distribución acumulada de latencias (todas las repeticiones)
  docs/evidencia/comparacion_recursos.png     CPU media de API, Cassandra, Redis, generador y SO

Uso: python scripts/comparar_resultados.py linea_base optimizada_cache optimizada_cache_workers
"""
import csv
import json
import re
import statistics
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import comun  # noqa: E402

NOMBRES = {"linea_base": "Línea base", "optimizada_cache": "Opt. 1: caché Redis",
           "optimizada_cache_workers": "Opt. 1+2: caché + 3 workers", "optimizada_workers": "Opt. 2 sola: 3 workers"}


def corridas(config: str) -> list[dict]:
    salida = []
    for carpeta in sorted(comun.EVIDENCIA.glob(f"{config}_r*_*")):
        if not re.fullmatch(rf"{config}_r\d+_\d{{8}}T\d{{6}}Z", carpeta.name):
            continue
        d = {"carpeta": carpeta, "resumen": json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))}
        for extra in ("servidor", "integridad"):
            f = carpeta / f"{extra}.json"
            d[extra] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        salida.append(d)
    return salida


def med(valores):
    valores = [v for v in valores if v is not None]
    return (statistics.median(valores), min(valores), max(valores)) if valores else (None, None, None)


def fmt(t, dec=0):
    m, lo, hi = t
    if m is None:
        return "-"
    return f"{m:.{dec}f} ({lo:.{dec}f}–{hi:.{dec}f})" if lo != hi else f"{m:.{dec}f}"


def main():
    configs = sys.argv[1:] or ["linea_base", "optimizada_cache", "optimizada_cache_workers"]
    datos = {c: corridas(c) for c in configs}
    datos = {c: v for c, v in datos.items() if v}
    filas = []
    for c, rs in datos.items():
        g = [r["resumen"]["global"] for r in rs]
        rec = [r["resumen"]["recursos_sostenimiento_media"] for r in rs]
        srv = [r["servidor"].get("leer", {}) for r in rs]
        filas.append({
            "config": c, "n": len(rs), "commit": ", ".join(sorted({r["resumen"]["commit"] for r in rs})),
            "rps": med([x["throughput_rps"] for x in g]), "req": med([x["requests"] for x in g]),
            "p50": med([x["latencia_ms"]["p50"] for x in g]), "p95": med([x["latencia_ms"]["p95"] for x in g]),
            "p99": med([x["latencia_ms"]["p99"] for x in g]), "max": med([x["latencia_ms"]["max"] for x in g]),
            "err": med([x["tasa_error_pct"] for x in g]),
            "srv_p50": med([s.get("p50") for s in srv]), "srv_p95": med([s.get("p95") for s in srv]),
            "api_cpu": med([x["api_cpu_pct"] for x in rec]), "api_mem": med([x["api_mem_mb"] for x in rec]),
            "cas_cpu": med([x["cassandra_cpu_pct"] for x in rec]), "redis_cpu": med([x["redis_cpu_pct"] for x in rec]),
            "gen_cpu": med([x["generador_cpu_pct"] for x in rec]), "so_cpu": med([x["so_cpu_pct"] for x in rec]),
            "integridad": all(r["integridad"].get("integridad_ok") for r in rs),
            "escrituras": sum(r["integridad"].get("escrituras", {}).get("aceptadas_201", 0) for r in rs),
            "corridas": [r["carpeta"].name for r in rs],
        })

    base = filas[0]
    lineas = ["# Comparación antes / después (generado por scripts/comparar_resultados.py)", "",
              "Valores: **mediana entre repeticiones** y, entre paréntesis, mínimo–máximo. Métricas del período de "
              "sostenimiento (120 s, 60 VU). Latencia = tiempo de respuesta HTTP visto por el generador, en ms. "
              "Latencia del servidor = duración registrada por la API para las lecturas de comentarios. CPU en % de un "
              "núcleo (100 = 1 núcleo), media de muestras cada 2 s.", "",
              "| Métrica | " + " | ".join(NOMBRES.get(f["config"], f["config"]) for f in filas) + " |",
              "|---|" + "---|" * len(filas)]

    def fila(nombre, clave, dec=0):
        lineas.append(f"| {nombre} | " + " | ".join(fmt(f[clave], dec) for f in filas) + " |")

    lineas.append("| Repeticiones | " + " | ".join(str(f["n"]) for f in filas) + " |")
    fila("Throughput (req/s)", "rps", 1)
    fila("Requests en el sostenimiento", "req")
    fila("Latencia p50 (ms)", "p50", 1)
    fila("Latencia p95 (ms)", "p95", 1)
    fila("Latencia p99 (ms)", "p99", 1)
    fila("Latencia máxima (ms)", "max", 1)
    fila("Tasa de error (%)", "err", 2)
    fila("Servidor: lectura p50 (ms)", "srv_p50", 1)
    fila("Servidor: lectura p95 (ms)", "srv_p95", 1)
    fila("CPU API (% de 1 núcleo)", "api_cpu")
    fila("Memoria API (MB)", "api_mem")
    fila("CPU Cassandra (%)", "cas_cpu")
    fila("CPU Redis (%)", "redis_cpu")
    fila("CPU generador (%)", "gen_cpu")
    fila("CPU total del SO (% del equipo)", "so_cpu")
    lineas.append("| Integridad OK en todas las corridas | " + " | ".join("sí" if f["integridad"] else "**NO**" for f in filas) + " |")
    lineas.append("| Escrituras verificadas (suma) | " + " | ".join(str(f["escrituras"]) for f in filas) + " |")
    lineas.append("| Commit | " + " | ".join(f["commit"] for f in filas) + " |")
    lineas += ["", "## Variación respecto de la línea base (medianas)", "",
               "| Configuración | Throughput | p50 | p95 | p99 | CPU API | CPU Cassandra |", "|---|---|---|---|---|---|---|"]
    for f in filas[1:]:
        def pct(k):
            b, v = base[k][0], f[k][0]
            return f"{(v - b) / b * 100:+.0f} %" if b else "-"
        lineas.append(f"| {NOMBRES.get(f['config'], f['config'])} | {pct('rps')} | {pct('p50')} | {pct('p95')} | "
                      f"{pct('p99')} | {pct('api_cpu')} | {pct('cas_cpu')} |")
    lineas += ["", "## Corridas incluidas", ""] + [f"- {f['config']}: " + ", ".join(f"`{c}`" for c in f["corridas"])
                                                   for f in filas]
    (comun.EVIDENCIA / "comparacion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    etiquetas = [NOMBRES.get(f["config"], f["config"]) for f in filas]
    # Latencias
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ancho = 0.25
    for i, (k, color) in enumerate([("p50", "#4C78A8"), ("p95", "#F58518"), ("p99", "#E45756")]):
        xs = [j + (i - 1) * ancho for j in range(len(filas))]
        ys = [f[k][0] for f in filas]
        err = [[f[k][0] - f[k][1] for f in filas], [f[k][2] - f[k][0] for f in filas]]
        ax.bar(xs, ys, ancho, label=k, color=color, yerr=err, capsize=3)
        for x, y in zip(xs, ys):
            ax.text(x, y, f"{y:.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(filas)), etiquetas)
    ax.set_ylabel("ms (mediana; barra de error = mín–máx)")
    ax.set_title("Latencia del flujo de comentarios en vivo (60 VU, 120 s sostenidos)")
    ax.legend()
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(comun.EVIDENCIA / "comparacion_latencias.png", dpi=110)

    # Distribución acumulada
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for f, et in zip(filas, etiquetas):
        lat = []
        for c in f["corridas"]:
            with (comun.EVIDENCIA / c / "requests.csv").open(encoding="utf-8") as fh:
                lat += [float(r["latencia_ms"]) for r in csv.DictReader(fh) if r["etapa"] == "sostenimiento"]
        lat.sort()
        ax.plot(lat, [i / len(lat) for i in range(len(lat))], label=f"{et} (n={len(lat)})")
    ax.set_xscale("log")
    ax.set_xlabel("latencia (ms, escala log)")
    ax.set_ylabel("proporción de requests ≤ x")
    ax.set_title("Distribución acumulada de latencias (todas las repeticiones)")
    ax.grid(alpha=.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(comun.EVIDENCIA / "comparacion_distribucion.png", dpi=110)

    # Recursos
    fig, ax = plt.subplots(figsize=(9, 4.5))
    claves = [("api_cpu", "API"), ("cas_cpu", "Cassandra"), ("redis_cpu", "Redis"), ("gen_cpu", "Generador")]
    ancho = 0.2
    for i, (k, n) in enumerate(claves):
        xs = [j + (i - 1.5) * ancho for j in range(len(filas))]
        ax.bar(xs, [f[k][0] for f in filas], ancho, label=n)
    ax.set_xticks(range(len(filas)), etiquetas)
    ax.set_ylabel("% de un núcleo (media en el sostenimiento)")
    ax.set_title("Uso de CPU por componente")
    ax.legend()
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(comun.EVIDENCIA / "comparacion_recursos.png", dpi=110)
    print((comun.EVIDENCIA / "comparacion.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
