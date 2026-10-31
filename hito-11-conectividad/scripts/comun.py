"""Configuración y registro de resultados compartidos por las pruebas del Hito 11.

Cada prueba imprime una línea legible y, si RESULTADOS apunta a un archivo, agrega una línea JSON con
producto, capa, prueba, resultado, duración y diagnóstico. Ninguna salida incluye secretos: los
valores de las variables sensibles se reemplazan por "definida" o "no definida".
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent.parent
SECRETOS = ("PASSWORD", "TOKEN", "SECRET")
# Orden de la secuencia de evaluación (5.2 de la consigna): de menor a mayor costo.
CAPAS = ("configuracion", "resolucion", "tcp", "protocolo", "autenticacion", "autorizacion", "contexto",
         "lectura", "api")


def _leer_env(ruta: Path) -> dict:
    valores = {}
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.split(" #")[0].strip()
    return valores


def cargar_config() -> dict:
    """config/local.env (o el ejemplo) + el .env de la API. Las variables de entorno tienen prioridad."""
    propia = RAIZ / "config" / "local.env"
    config = _leer_env(propia if propia.exists() else RAIZ / "config" / "configuracion-ejemplo.env")
    config.update(_leer_env((RAIZ / config.get("ENV_API", "../hito-10-api/.env")).resolve()))
    config.update({k: v for k, v in os.environ.items() if k in config or k.startswith(("API_", "TIMEOUT_S"))})
    config["TIMEOUT_S"] = float(config.get("TIMEOUT_S", 3))
    return config


def es_secreto(clave: str) -> bool:
    return any(s in clave.upper() for s in SECRETOS)


def mostrar(clave: str, valor) -> str:
    """Valor apto para la evidencia: oculta secretos y credenciales dentro de una URI."""
    if es_secreto(clave):
        return "definida (oculta)" if valor else "no definida"
    return re.sub(r"//[^/@\s]+@", "//***@", str(valor))


def host_puerto(url: str, puerto_por_defecto: int) -> tuple[str, int]:
    partes = urlsplit(url if "://" in url else f"x://{url}")
    return partes.hostname or "", partes.port or puerto_por_defecto


class Registro:
    """Acumula y muestra los resultados de un producto."""

    def __init__(self, producto: str):
        self.producto = producto
        self.archivo = os.environ.get("RESULTADOS")

    def anotar(self, capa: str, prueba: str, resultado: str, detalle: str, ms: float | None = None,
               tipo: str = "capa"):
        """resultado: OK (la prueba dio lo esperado), FALLA o SKIP (no se ejecutó por falta de
        herramienta o configuración: no significa que el producto esté caído).
        tipo: capa (secuencia de evaluación) o contraste (caso negativo que debe fallar de una forma)."""
        duracion = f"{ms:7.1f} ms" if ms is not None else " " * 10
        print(f"{resultado:<5} {self.producto:<9} {capa:<13} {duracion}  {prueba}: {detalle}", flush=True)
        if self.archivo:
            with open(self.archivo, "a", encoding="utf-8") as f:
                f.write(json.dumps({"fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "producto": self.producto, "capa": capa, "tipo": tipo, "prueba": prueba,
                                    "resultado": resultado, "ms": ms, "detalle": detalle},
                                   ensure_ascii=False) + "\n")

    def medir(self, capa: str, prueba: str, funcion, esperado: str = "", tipo: str = "capa"):
        """Ejecuta funcion(); si devuelve un texto, es el detalle. Si lanza una excepción, es FALLA con
        el tipo de error (nunca el mensaje completo, que puede incluir URIs o usuarios)."""
        inicio = time.perf_counter()
        try:
            detalle = funcion() or esperado
            self.anotar(capa, prueba, "OK", detalle, (time.perf_counter() - inicio) * 1000, tipo)
            return True
        except Exception as e:  # el diagnóstico registra cualquier falla y sigue con la siguiente prueba
            self.anotar(capa, prueba, "FALLA", f"{type(e).__name__}: {resumen(e)}",
                        (time.perf_counter() - inicio) * 1000, tipo)
            return False


def resumen(e: Exception) -> str:
    """Primera línea del error, sin credenciales y acotada."""
    texto = str(e).strip().splitlines()[0] if str(e).strip() else ""
    return mostrar("", texto)[:140]
