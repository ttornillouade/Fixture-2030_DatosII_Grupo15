"""Configuración compartida por los scripts del Hito 12.

Todo lo que identifica a los datos de laboratorio está acá, para que preparar, validar y limpiar
toquen exactamente los mismos registros (RNF7, RNF11):
  - partidos de laboratorio P901-P904 (no existen en el fixture real: el Hito 5 llega a P128);
  - usuarios de laboratorio U900000-U909999.
"""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EVIDENCIA = RAIZ / "docs" / "evidencia"
API_DIR = RAIZ.parent / "hito-10-api"

PARTIDOS_LAB = ["P901", "P902", "P903", "P904"]
USUARIO_MIN, USUARIO_MAX = 900000, 909999
SHARDS = 8  # el mismo valor que app/adaptadores/cassandra.py (Hito 6)
KEYSPACE = os.environ.get("CASSANDRA_KEYSPACE", "fixture2030_comments")
CASSANDRA_HOST = os.environ.get("CASSANDRA_HOST", "127.0.0.1")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


def usuario(n: int) -> str:
    return f"U{USUARIO_MIN + n % (USUARIO_MAX - USUARIO_MIN + 1):06d}"


def bucket_de(t: datetime) -> datetime:
    return t.replace(minute=t.minute - t.minute % 5, second=0, microsecond=0)


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def commit_actual() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                             text=True, check=True).stdout.strip()
        sucio = subprocess.run(["git", "status", "--porcelain", "--", str(RAIZ.parent / "hito-10-api" / "app")],
                               cwd=RAIZ, capture_output=True, text=True).stdout.strip()
        return sha + ("+cambios-sin-commit-en-app" if sucio else "")
    except Exception:
        return "desconocido"


def versiones_imagenes() -> dict:
    """Versión observada de cada contenedor (imagen + digest), para la trazabilidad (RNF2)."""
    salida = {}
    for nombre in ["mongodb", "redis", "cassandra", "neo4j", "influxdb", "iris"]:
        c = f"fixture2030-{nombre}"
        r = subprocess.run(["docker", "inspect", "-f", "{{.Config.Image}} {{.Image}}", c],
                           capture_output=True, text=True)
        salida[c] = r.stdout.strip()[:90] if r.returncode == 0 else "no encontrado"
    r = subprocess.run(["docker", "exec", "fixture2030-cassandra", "nodetool", "version"], capture_output=True, text=True)
    salida["cassandra_release"] = r.stdout.strip()
    return salida


def guardar_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def sesion_cassandra():
    from cassandra.cluster import Cluster
    cluster = Cluster([CASSANDRA_HOST], port=9042, connect_timeout=10)
    s = cluster.connect(KEYSPACE)
    s.default_timeout = 30
    return cluster, s


def ventana_historica(inicio: datetime, horas: int) -> list[datetime]:
    return [inicio + timedelta(minutes=5 * i) for i in range(horas * 12)]
