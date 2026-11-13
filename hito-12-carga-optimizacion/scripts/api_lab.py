"""Inicia o detiene la API del Hito 10 para una corrida de laboratorio.

  python scripts/api_lab.py iniciar --log <archivo> [--workers 1] [--cache-ttl-ms 0]
  python scripts/api_lab.py detener

Es lo mismo que hito-10-api/scripts/iniciar_api.sh, pero en segundo plano, con la configuración de
la corrida explícita (workers y caché) y guardando el PID para poder medir su CPU y detenerla.
La configuración de conexión sigue saliendo de hito-10-api/.env (no versionado).
"""
import argparse
import os
import subprocess
import sys
import time

import httpx
import psutil

import comun

PID = comun.RAIZ / "config" / "api.pid"   # ignorado por git


def _python_api() -> str:
    venv = comun.API_DIR / ".venv"
    return str(venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))


def iniciar(log: str, workers: int, cache_ttl_ms: int) -> None:
    try:
        httpx.get(f"{comun.API_URL}/salud", timeout=1)
        sys.exit("Ya hay una API escuchando en el puerto 8000: detenerla antes (python scripts/api_lab.py detener)")
    except httpx.HTTPError:
        pass
    env = dict(os.environ, CACHE_COMENTARIOS_TTL_MS=str(cache_ttl_ms))
    cmd = [_python_api(), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000",
           "--no-access-log", "--workers", str(workers)]
    with open(log, "w", encoding="utf-8") as salida:
        p = subprocess.Popen(cmd, cwd=comun.API_DIR, env=env, stdout=salida, stderr=subprocess.STDOUT)
    PID.write_text(str(p.pid))
    for _ in range(60):
        try:
            if httpx.get(f"{comun.API_URL}/salud", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.5)
    else:
        sys.exit(f"La API no respondió /salud en 30 s: ver {log}")
    # Primer request a cada base para abrir los pools antes de medir (no forma parte de la medición).
    httpx.get(f"{comun.API_URL}/salud/dependencias", timeout=10)
    print(p.pid)


def detener() -> None:
    if not PID.exists():
        return
    try:
        raiz = psutil.Process(int(PID.read_text()))
        procesos = raiz.children(recursive=True) + [raiz]
        for p in procesos:
            p.terminate()
        psutil.wait_procs(procesos, timeout=10)
    except psutil.NoSuchProcess:
        pass
    PID.unlink()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["iniciar", "detener"])
    ap.add_argument("--log", default=str(comun.RAIZ / "config" / "api.log"))
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--cache-ttl-ms", type=int, default=0)
    a = ap.parse_args()
    iniciar(a.log, a.workers, a.cache_ttl_ms) if a.accion == "iniciar" else detener()
