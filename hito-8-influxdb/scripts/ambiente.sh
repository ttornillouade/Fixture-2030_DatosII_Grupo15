#!/usr/bin/env bash
# Registra el ambiente de ejecución (RNF10): fecha, SO, CPU, RAM, Docker y versión de InfluxDB.
. "$(dirname "$0")/comun.sh"
echo "Fecha local:  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Fecha UTC:    $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "SO:           $(uname -srm)"
if command -v sysctl >/dev/null && sysctl -n machdep.cpu.brand_string >/dev/null 2>&1; then
  echo "CPU:          $(sysctl -n machdep.cpu.brand_string) ($(sysctl -n hw.ncpu) núcleos)"
  echo "RAM:          $(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 )) GB"
elif command -v lscpu >/dev/null; then
  echo "CPU:          $(lscpu | awk -F: '/Model name/ {gsub(/^ +/,"",$2); print $2}') ($(nproc) núcleos)"
  echo "RAM:          $(free -g | awk '/Mem:/ {print $2}') GB"
fi
echo "Docker:       $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '?')"
echo "Recursos VM Docker: $(docker info --format 'CPUs={{.NCPU}} Mem={{.MemTotal}} bytes' 2>/dev/null || echo '?')"
echo "Python:       $("$PY" --version 2>&1)"
echo "InfluxDB:     $(influx --version 2>/dev/null || echo 'contenedor no disponible')"
docker image inspect influxdb:3-core --format 'Imagen:       influxdb:3-core {{index .RepoDigests 0}}' 2>/dev/null || true
