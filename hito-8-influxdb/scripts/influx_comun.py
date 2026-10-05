"""Utilidades compartidas del Hito 8 (solo librería estándar, Python >= 3.9).

- Lee la configuración desde variables de entorno o desde ../.env
- Cliente HTTP mínimo para InfluxDB 3 (/api/v3/write_lp y /api/v3/query_sql)
- Manifiesto de la última generación (data/generated/<run>/manifest.json)
- Formateo de line protocol y de tablas de texto
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_GENERADOS = RAIZ / "data" / "generated"
DIR_EVIDENCIA = RAIZ / "docs" / "evidencia"

PRECISION_LP = "millisecond"  # precisión declarada de TODOS los timestamps (RNF6)


# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
def _leer_env_archivo() -> dict:
    valores = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


_ENV_ARCHIVO = _leer_env_archivo()


def cfg(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre) or _ENV_ARCHIVO.get(nombre) or defecto


URL = cfg("INFLUX_URL", "http://localhost:" + cfg("INFLUX_PORT", "8181")).rstrip("/")
DB_VIVO = cfg("INFLUX_DB_VIVO", "fixture2030_vivo")
DB_HISTORICO = cfg("INFLUX_DB_HISTORICO", "fixture2030_historico")


def token() -> str:
    t = cfg("INFLUX_TOKEN")
    if not t:
        sys.exit("ERROR: falta INFLUX_TOKEN. Ejecutar primero: bash scripts/autorizacion.sh")
    return t


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
class ErrorHTTP(Exception):
    def __init__(self, status: int, cuerpo: str):
        super().__init__(f"HTTP {status}: {cuerpo[:500]}")
        self.status = status
        self.cuerpo = cuerpo


def _request(metodo: str, ruta: str, cuerpo: bytes | None = None,
             headers: dict | None = None, timeout: float = 120) -> tuple[int, str]:
    h = {"Authorization": "Bearer " + token()}
    if headers:
        h.update(headers)
    req = urllib.request.Request(URL + ruta, data=cuerpo, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise ErrorHTTP(e.code, e.read().decode("utf-8", "replace")) from None


def escribir_lp(db: str, lineas: str | bytes, precision: str = PRECISION_LP,
                timeout: float = 120) -> dict:
    """POST /api/v3/write_lp. Devuelve {'ok':bool,'rechazadas':[...]}.

    Con accept_partial=true (valor por defecto del servidor) las líneas válidas se
    escriben aunque haya líneas inválidas; el 400 trae el detalle de cada rechazo.
    """
    if isinstance(lineas, str):
        lineas = lineas.encode("utf-8")
    q = urllib.parse.urlencode({"db": db, "precision": precision, "accept_partial": "true"})
    try:
        _request("POST", "/api/v3/write_lp?" + q, lineas,
                 {"Content-Type": "text/plain; charset=utf-8"}, timeout)
        return {"ok": True, "rechazadas": []}
    except ErrorHTTP as e:
        if e.status == 400:
            try:
                det = json.loads(e.cuerpo)
                data = det.get("data") or []
                if isinstance(data, dict):
                    data = [data]
                return {"ok": False, "rechazadas": data, "error": det.get("error", "")}
            except ValueError:
                pass
        raise


def consultar(db: str, sql: str, timeout: float = 300) -> list[dict]:
    """POST /api/v3/query_sql con formato JSONL. Devuelve una lista de filas (dict)."""
    cuerpo = json.dumps({"db": db, "q": sql, "format": "jsonl"}).encode("utf-8")
    _, texto = _request("POST", "/api/v3/query_sql", cuerpo,
                        {"Content-Type": "application/json"}, timeout)
    filas = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea:
            filas.append(json.loads(linea))
    return filas


def servidor_disponible(timeout: float = 3) -> bool:
    """True si el puerto HTTP responde (aunque responda 401 por falta de token)."""
    try:
        with urllib.request.urlopen(URL + "/health", timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Tiempo
# --------------------------------------------------------------------------- #
def ms_a_iso(ms: int) -> str:
    """Epoch ms -> literal RFC3339 UTC con milisegundos (para SQL)."""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


def iso_a_ms(texto: str) -> int:
    """'2026-10-04T12:00:00.123456' (como lo devuelve InfluxDB, sin Z) -> epoch ms."""
    t = texto.strip().replace(" ", "T")
    if t.endswith("Z"):
        t = t[:-1]
    if "+" in t[10:]:
        t = t[:10] + t[10:].split("+")[0]
    if "." in t:
        base, frac = t.split(".", 1)
        frac = (frac + "000000")[:6]
    else:
        base, frac = t, "000000"
    dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp()) * 1000 + int(frac) // 1000


# --------------------------------------------------------------------------- #
# Line protocol
# --------------------------------------------------------------------------- #
_ESC_TAG = re.compile(r"([,= ])")


def esc_tag(v: str) -> str:
    return _ESC_TAG.sub(r"\\\1", str(v))


def fmt_campo(v) -> str:
    """Tipos explícitos: bool -> true/false, int -> 12i, float -> 1.5, str -> "x"."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return f"{v}i"
    if isinstance(v, float):
        return f"{v:.4f}"  # siempre con punto decimal: el tipo float queda explícito
    s = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def linea_lp(tabla: str, tags: dict, campos: dict, ts_ms: int) -> str:
    t = ",".join(f"{k}={esc_tag(v)}" for k, v in tags.items())
    c = ",".join(f"{k}={fmt_campo(v)}" for k, v in campos.items() if v is not None)
    return f"{tabla},{t} {c} {ts_ms}" if t else f"{tabla} {c} {ts_ms}"


# --------------------------------------------------------------------------- #
# Manifiesto
# --------------------------------------------------------------------------- #
def dir_corrida(nombre: str | None = None) -> Path:
    if nombre:
        p = Path(nombre)
        return p if p.is_absolute() or p.exists() else DIR_GENERADOS / nombre
    ultimo = DIR_GENERADOS / "ULTIMA"
    if ultimo.exists():
        return DIR_GENERADOS / ultimo.read_text().strip()
    sys.exit("ERROR: no hay datos generados. Ejecutar: python3 scripts/generacion_puntos.py")


def cargar_manifiesto(nombre: str | None = None) -> dict:
    ruta = dir_corrida(nombre) / "manifest.json"
    if not ruta.exists():
        sys.exit(f"ERROR: no existe {ruta}")
    return json.loads(ruta.read_text(encoding="utf-8"))


def variables_sql(man: dict) -> dict:
    """Variables {{...}} que usan los archivos sql/ (derivadas del manifiesto)."""
    # Partido de referencia: el primero con goles (para que las consultas de eventos
    # e impacto en tráfico tengan algo que mostrar); si no hay, el primero.
    con_goles = [x for x in man["partidos"]
                 if sum(c["goles"] for c in x["consistencia"].values()) > 0]
    p = (con_goles or man["partidos"])[0]
    ini = p["inicio_ms"]
    v = {
        "DB_VIVO": DB_VIVO,
        "DB_HISTORICO": DB_HISTORICO,
        "PARTIDO": p["partido_id"],
        "EQUIPO_LOCAL": p["local"],
        "EQUIPO_VISITANTE": p["visitante"],
        "JUGADOR": p["local"] + "J09",
        "SEDE": p["sede_id"],
        "PARTIDO_DESDE": ms_a_iso(p["previa_ms"]),
        "PARTIDO_HASTA": ms_a_iso(p["post_ms"]),
        "JUEGO_DESDE": ms_a_iso(ini),
        "JUEGO_HASTA": ms_a_iso(p["fin_ms"]),
        # ventana del minuto 60 al 65 (segundo tiempo)
        "VENTANA_DESDE": ms_a_iso(p["st_inicio_ms"] + 15 * 60_000),
        "VENTANA_HASTA": ms_a_iso(p["st_inicio_ms"] + 20 * 60_000),
        # entretiempo +-10 min, para mostrar ausencia de puntos
        "HT_DESDE": ms_a_iso(p["pt_fin_ms"] - 10 * 60_000),
        "HT_HASTA": ms_a_iso(p["st_inicio_ms"] + 10 * 60_000),
        "TORNEO_DESDE": ms_a_iso(man["rango"]["desde_ms"]),
        "TORNEO_HASTA": ms_a_iso(man["rango"]["hasta_ms"]),
    }
    return v


def sustituir(sql: str, variables: dict) -> str:
    def rep(m):
        k = m.group(1)
        if k not in variables:
            raise KeyError(f"variable SQL desconocida: {{{{{k}}}}}")
        return str(variables[k])
    return re.sub(r"\{\{(\w+)\}\}", rep, sql)


# --------------------------------------------------------------------------- #
# Salida
# --------------------------------------------------------------------------- #
def tabla_texto(filas: list[dict], max_filas: int = 40) -> str:
    if not filas:
        return "(sin filas)"
    cols = []
    for f in filas:
        for k in f:
            if k not in cols:
                cols.append(k)

    def celda(v):
        if v is None:
            return "NULL"
        if isinstance(v, float):
            return f"{v:.3f}"
        return str(v)

    mostrar = filas[:max_filas]
    anchos = {c: max(len(c), *(len(celda(f.get(c))) for f in mostrar)) for c in cols}
    sep = "+" + "+".join("-" * (anchos[c] + 2) for c in cols) + "+"
    out = [sep, "| " + " | ".join(c.ljust(anchos[c]) for c in cols) + " |", sep]
    for f in mostrar:
        out.append("| " + " | ".join(celda(f.get(c)).ljust(anchos[c]) for c in cols) + " |")
    out.append(sep)
    if len(filas) > max_filas:
        out.append(f"... {len(filas) - max_filas} filas más (total {len(filas)})")
    else:
        out.append(f"{len(filas)} filas")
    return "\n".join(out)


def ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sello() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def cronometro():
    return time.perf_counter()
