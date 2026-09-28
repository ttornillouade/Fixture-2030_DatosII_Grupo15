#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. Invalidacion inicial para forzar MISS ==="
python3 scripts/cache_aside.py invalidate E001

echo
echo "=== 2. Primera lectura: MISS -> fuente de verdad demo -> Redis ==="
python3 scripts/cache_aside.py get E001

echo
echo "=== 3. Segunda lectura: HIT ==="
python3 scripts/cache_aside.py get E001

echo
echo "=== 4. Cambio en fuente de verdad: estrategia = invalidar ==="
python3 scripts/cache_aside.py invalidate E001

echo
echo "=== 5. Nueva lectura: MISS y reconstruccion ==="
python3 scripts/cache_aside.py get E001
