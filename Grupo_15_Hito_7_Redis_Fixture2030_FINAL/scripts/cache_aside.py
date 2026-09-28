#!/usr/bin/env python3
"""
Demostración local del patrón cache-aside.

La fuente de verdad real del TPO para Equipo continúa siendo el módulo documental
del Hito 4. El JSON local es únicamente una respuesta reproducible para el laboratorio
de Redis, ya que el Hito 7 no exige integración física entre motores.

Uso:
  python3 scripts/cache_aside.py get E001
  python3 scripts/cache_aside.py invalidate E001
"""
import json
import os
import subprocess
import sys
from pathlib import Path

CONTAINER = os.getenv("REDIS_CONTAINER_NAME", "fixture2030-redis")
SOURCE = Path("data/fuente_verdad_equipos_demo.json")
TTL_SECONDS = 300

def redis(*args, raw=False):
    cmd = ["docker", "exec", CONTAINER, "redis-cli"]
    if raw:
        cmd.append("--raw")
    cmd.extend(map(str, args))
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()

def load_source(equipo_id):
    rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    for row in rows:
        if row["id"] == equipo_id:
            return row
    return None

def parse_hgetall(text):
    if not text:
        return {}
    lines = text.splitlines()
    return dict(zip(lines[0::2], lines[1::2]))

def get(equipo_id):
    key = f"fixture2030:cache:equipo:{equipo_id}"
    cached = parse_hgetall(redis("HGETALL", key, raw=True))
    if cached:
        print("CACHE_HIT")
        print(json.dumps(cached, ensure_ascii=False, indent=2))
        print("TTL:", redis("TTL", key))
        return

    print("CACHE_MISS")
    source = load_source(equipo_id)
    if source is None:
        print("SOURCE_NOT_FOUND")
        return

    args = ["HSET", key]
    for field, value in source.items():
        args += [field, value]
    redis(*args)
    redis("EXPIRE", key, TTL_SECONDS)

    print("SOURCE_OF_TRUTH_DEMO -> CACHE")
    print(json.dumps(source, ensure_ascii=False, indent=2))
    print("TTL:", redis("TTL", key))

def invalidate(equipo_id):
    key = f"fixture2030:cache:equipo:{equipo_id}"
    deleted = redis("DEL", key)
    print("INVALIDATED:", deleted)

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "get"
    equipo_id = sys.argv[2] if len(sys.argv) > 2 else "E001"

    if action == "get":
        get(equipo_id)
    elif action == "invalidate":
        invalidate(equipo_id)
    else:
        raise SystemExit("Uso: cache_aside.py [get|invalidate] E001")
