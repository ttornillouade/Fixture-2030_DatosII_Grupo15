"""Matriz de conectividad: un estado por producto a partir de los resultados de una ejecución (JSONL).

Estados (RNF9):
  up              todas las capas probadas hasta la lectura dieron OK (y la API, si se probó).
  down            falló una capa: el diagnóstico es la primera capa que falló, en el orden de 5.2.
  degraded        el producto responde a su cliente, pero la ruta de la API falla (o al revés).
  not_configured  faltan variables de configuración: el módulo no está preparado en este entorno.
  unknown         se probó algo, pero no alcanza para concluir: no se llegó a la lectura (por ejemplo,
                  modo tcp). Un puerto abierto no prueba protocolo, identidad ni contexto.
  not_tested      no se ejecutó ninguna prueba de ese producto en esta corrida (--producto lo dejó afuera).
Los contrastes (casos negativos) no cambian el estado: se cuentan aparte.
Uso: python resumen.py resultados.jsonl
"""
import json
import sys
from collections import defaultdict

from comun import CAPAS

PRODUCTOS = ("mongodb", "neo4j", "cassandra", "redis", "influxdb", "iris", "api")

filas = defaultdict(list)
with open(sys.argv[1], encoding="utf-8") as f:
    for linea in f:
        resultado = json.loads(linea)
        filas[resultado["producto"]].append(resultado)


def estado(pruebas: list[dict]) -> tuple[str, str]:
    capas = [p for p in pruebas if p["tipo"] == "capa"]
    if any(p["capa"] == "configuracion" and p["resultado"] == "FALLA" for p in capas):
        return "not_configured", "faltan variables de configuración"
    fallas = sorted((p for p in capas if p["resultado"] == "FALLA"), key=lambda p: CAPAS.index(p["capa"]))
    nativas = [p for p in fallas if p["capa"] != "api"]
    api = [p for p in fallas if p["capa"] == "api"]
    leyo = any(p["capa"] == "lectura" and p["resultado"] == "OK" for p in capas)
    probo_api = any(p["capa"] == "api" for p in capas)
    if nativas and probo_api and not api:
        return "degraded", f"la API responde, pero falla {nativas[0]['capa']}: {nativas[0]['detalle']}"
    if nativas:
        return "down", f"falla en {nativas[0]['capa']}: {nativas[0]['prueba']}: {nativas[0]['detalle']}"
    if api and leyo:
        return "degraded", f"el cliente nativo lee, pero la API falla: {api[0]['detalle'][:90]}"
    if api:
        return "down", f"falla la API: {api[0]['detalle'][:90]}"
    if not leyo and not probo_api:
        return "unknown", "no se probó la lectura: un puerto abierto no prueba protocolo, identidad ni contexto"
    return "up", "todas las capas probadas respondieron"


def latencia(pruebas: list[dict], capa: str) -> str:
    valores = [p["ms"] for p in pruebas if p["capa"] == capa and p["tipo"] == "capa" and p["ms"] is not None]
    return f"{max(valores):.0f} ms" if valores else "—"


print("| Producto | Estado | TCP | Lectura | API | Capas OK / FALLA / SKIP | Contrastes OK / FALLA | Diagnóstico |")
print("|---|---|---|---|---|---|---|---|")
for producto in PRODUCTOS:
    pruebas = filas.get(producto)
    if not pruebas:
        print(f"| {producto} | not_tested | — | — | — | — | — | no se ejecutó ninguna prueba en esta corrida |")
        continue
    nombre, diagnostico = estado(pruebas)
    capas = [p["resultado"] for p in pruebas if p["tipo"] == "capa"]
    contrastes = [p["resultado"] for p in pruebas if p["tipo"] == "contraste"]
    print(f"| {producto} | **{nombre}** | {latencia(pruebas, 'tcp')} | {latencia(pruebas, 'lectura')} | "
          f"{latencia(pruebas, 'api')} | {capas.count('OK')} / {capas.count('FALLA')} / {capas.count('SKIP')} | "
          f"{contrastes.count('OK')} / {contrastes.count('FALLA')} | {diagnostico.replace('|', '/')} |")
print("\nLatencias: la máxima de cada capa en esta ejecución. Miden una prueba puntual, no rendimiento (RNF17).")
