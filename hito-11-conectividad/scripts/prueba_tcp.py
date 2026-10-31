"""Configuración, resolución de nombres y conexión TCP, desde el mismo entorno que la API (la notebook).

Responde: ¿la configuración está completa?, ¿el host se resuelve desde acá?, ¿hay un listener en ese
puerto? No responde todavía si el protocolo, la identidad o el contexto son válidos: eso lo prueba
prueba_clientes.py. Los contrastes muestran los otros resultados de la tabla 5.3 de la consigna.
Uso: python prueba_tcp.py [producto ...]
"""
import socket
import sys

from comun import Registro, cargar_config, host_puerto, mostrar

c = cargar_config()
T = c["TIMEOUT_S"]

# producto -> [(destino, variables de configuración, host, puerto)]
DESTINOS = {
    "mongodb": [("MongoDB", ("MONGODB_URI", "MONGODB_DATABASE"), *host_puerto(c.get("MONGODB_URI", ""), 27017))],
    "neo4j": [("Bolt", ("NEO4J_URI", "NEO4J_USUARIO", "NEO4J_PASSWORD"), *host_puerto(c.get("NEO4J_URI", ""), 7687)),
              ("HTTP (Browser)", ("NEO4J_HTTP_URL",), *host_puerto(c.get("NEO4J_HTTP_URL", ""), 7474))],
    "cassandra": [("CQL", ("CASSANDRA_HOST", "CASSANDRA_PORT", "CASSANDRA_KEYSPACE"),
                   c.get("CASSANDRA_HOST", ""), int(c.get("CASSANDRA_PORT", 9042)))],
    "redis": [("RESP", ("REDIS_URL",), *host_puerto(c.get("REDIS_URL", ""), 6379))],
    "influxdb": [("HTTP API", ("INFLUX_URL", "INFLUX_DATABASE", "INFLUX_TOKEN"), *host_puerto(c.get("INFLUX_URL", ""), 8181))],
    "iris": [("Superserver", ("IRIS_HOST", "IRIS_PORT", "IRIS_NAMESPACE", "IRIS_USUARIO", "IRIS_PASSWORD"),
              c.get("IRIS_HOST", ""), int(c.get("IRIS_PORT", 1972))),
             ("Portal HTTP", ("IRIS_PORTAL_URL",), *host_puerto(c.get("IRIS_PORTAL_URL", ""), 52773))],
}


def resolver(host: str) -> str:
    direcciones = sorted({info[4][0] for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})
    return f"{host} -> {', '.join(direcciones)}"


def conectar(host: str, puerto: int) -> str:
    """Clasifica el resultado como en la tabla 5.3: conexión, refused, timeout o host no resuelto."""
    try:
        with socket.create_connection((host, puerto), timeout=T):
            return "conexión exitosa: hay un listener"
    except ConnectionRefusedError:
        raise ConnectionRefusedError("connection refused: el host responde pero no hay listener en el puerto")
    except socket.timeout:
        raise TimeoutError(f"timeout: sin respuesta en {T:.0f} s (red, firewall, ruta o servicio colgado)")
    except socket.gaierror:
        raise LookupError("host no resuelto desde este entorno")


def esperar_falla(funcion, tipo: type, interpretacion: str):
    """Para los contrastes: la prueba es OK si falla exactamente de la forma esperada."""
    def prueba():
        try:
            funcion()
        except tipo as e:
            return f"{e} ({interpretacion})"
        raise AssertionError(f"se esperaba {tipo.__name__} y la conexión funcionó")
    return prueba


def configuracion(variables: tuple) -> str:
    faltan = [v for v in variables if not c.get(v)]
    if faltan:
        raise KeyError(f"faltan {', '.join(faltan)}")
    return ", ".join(f"{v}={mostrar(v, c[v])}" for v in variables)


def contrastes(r: Registro, producto: str):
    if producto == "mongodb":
        r.medir("resolucion", "nombre del servicio de Compose (mongodb:27017)",
                esperar_falla(lambda: conectar("mongodb", 27017), LookupError,
                              "ese nombre solo existe dentro de la red de Docker Compose"), tipo="contraste")
        r.medir("tcp", "puerto incorrecto (localhost:27018)",
                esperar_falla(lambda: conectar("localhost", 27018), ConnectionRefusedError,
                              "MongoDB está activo, pero en otro puerto"), tipo="contraste")
        r.medir("tcp", "host sin ruta (10.255.255.1:27017)",
                esperar_falla(lambda: conectar("10.255.255.1", 27017), TimeoutError,
                              "nadie contesta: así se ve una red bloqueada"), tipo="contraste")
    if producto == "cassandra":
        r.medir("tcp", "puerto interno no publicado (localhost:7199, JMX)",
                esperar_falla(lambda: conectar("localhost", 7199), ConnectionRefusedError,
                              "existe dentro del contenedor, pero Compose no lo publica"), tipo="contraste")
        # El 7000 es el puerto interno de gossip de Cassandra, pero en macOS lo ocupa AirPlay (ControlCenter):
        # el TCP conecta igual. prueba_clientes.py muestra que ahí no responde el protocolo CQL.
        r.medir("tcp", "puerto 7000 (gossip de Cassandra, no publicado)",
                lambda: conectar("localhost", 7000) + " (es otro proceso de la notebook: el TCP no prueba el producto)",
                tipo="contraste")


for producto in sys.argv[1:] or DESTINOS:
    r = Registro(producto)
    for destino, variables, host, puerto in DESTINOS[producto]:
        if not r.medir("configuracion", f"{destino}: variables", lambda: configuracion(variables)):
            continue
        if r.medir("resolucion", f"{destino}: {host}", lambda: resolver(host)):
            r.medir("tcp", f"{destino}: {host}:{puerto}", lambda: conectar(host, puerto))
    contrastes(r, producto)
