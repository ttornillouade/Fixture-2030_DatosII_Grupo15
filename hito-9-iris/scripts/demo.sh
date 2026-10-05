#!/usr/bin/env bash
# RF5–RF9 — Ejecuta la demostración completa (Fixture.Demo) en la terminal de IRIS.
# Uso: bash scripts/demo.sh [Seccion]   (por defecto: Ejecutar)
#   Secciones: Limpiar, CargarArbol, Navegar, FallasControladas, ReglasDeEstado, ProyeccionSQL, Integridad
. "$(dirname "$0")/comun.sh"
requiere_contenedor

SECCION="${1:-Ejecutar}"
iris_ejecutar "##class(Fixture.Demo).${SECCION}()"
