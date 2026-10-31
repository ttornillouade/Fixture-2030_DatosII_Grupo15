"""Límite de tiempo para los drivers que no tienen timeout de lectura (Neo4j e IRIS).

Esos drivers limitan la conexión, pero si la base la acepta y después no responde (por ejemplo, un
contenedor pausado) esperan sin límite. La operación corre en un hilo aparte: al vencer TIMEOUT_S la
request responde 504 y el hilo termina cuando la base responde o corta la conexión.
"""
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as Vencido

from app.config import config
from app.errores import DependenciaTimeout

# Pocos hilos a propósito: si todos quedan esperando a una base colgada, las requests siguientes
# esperan en la cola y responden 504 igual, sin crear hilos sin límite.
_hilos = ThreadPoolExecutor(max_workers=8, thread_name_prefix="limite")


def con_limite(fuente: str, operacion, *args, **kwargs):
    futuro = _hilos.submit(operacion, *args, **kwargs)
    try:
        return futuro.result(timeout=config.timeout_s)
    except Vencido:
        raise DependenciaTimeout(fuente, f"sin respuesta en {config.timeout_s:.0f} s (límite de la API)")
