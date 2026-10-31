"""Protocolo, identidad, contexto y lectura mínima de cada producto, con el mismo driver que usa la API.

Corre desde la notebook, el mismo origen que la API. Todas las operaciones son lecturas, pings o
consultas constantes. Los contrastes usan un contexto, una credencial o un recurso equivocados solo en
esa prueba, para mostrar en qué se diferencia cada falla.
Uso: python prueba_clientes.py [producto ...]
"""
import logging
import shutil
import sys

from comun import Registro, cargar_config, mostrar

c = cargar_config()
T = c["TIMEOUT_S"]
MS = int(T * 1000)
logging.disable(logging.WARNING)  # los drivers loguean sus reintentos: el resultado ya queda en el registro

# CLI nativo de cada producto en la notebook. Si no está instalado, esa prueba es SKIP: la evaluación
# sigue con el driver de Python, que es el cliente real de la API.
CLIS = {"mongodb": "mongosh", "neo4j": "cypher-shell", "cassandra": "cqlsh", "redis": "redis-cli",
        "influxdb": "influxdb3", "iris": "iris"}


def fallar(error: Exception):
    """Para usar dentro de una lambda: convierte una condición no cumplida en FALLA."""
    raise error


def contraste(funcion, esperado, interpretacion: str):
    """La prueba es OK si funcion() falla con la excepción esperada o devuelve lo que se espera."""
    def prueba():
        try:
            resultado = funcion()
        except Exception as e:
            if isinstance(esperado, type) and isinstance(e, esperado):
                return f"{type(e).__name__} ({interpretacion})"
            raise
        if isinstance(esperado, type) or resultado != esperado:
            raise AssertionError(f"se esperaba {getattr(esperado, '__name__', esperado)!r} y se obtuvo {resultado!r}")
        return f"{resultado!r} ({interpretacion})"
    return prueba


def mongodb(r: Registro):
    from pymongo import MongoClient
    uri, nombre = c["MONGODB_URI"], c["MONGODB_DATABASE"]
    cliente = MongoClient(uri, timeoutMS=MS, serverSelectionTimeoutMS=MS, connectTimeoutMS=MS)
    if not r.medir("protocolo", "handshake (hello)", lambda: f"MongoDB {cliente.server_info()['version']}"):
        return
    if "@" not in uri:
        r.anotar("autenticacion", "usuario de la URI", "SKIP", "la URI no tiene credenciales: el laboratorio corre sin autenticación")
        r.anotar("autorizacion", "roles del usuario", "SKIP", "sin autenticación no hay roles que verificar")
    db = cliente[nombre]
    r.medir("contexto", f"database {nombre}", lambda: (
        "colecciones equipos y jugadores presentes"
        if {"equipos", "jugadores"} <= set(db.list_collection_names()) else fallar(LookupError("faltan colecciones"))))
    r.medir("lectura", "equipos.find_one({_id: 'E010'})", lambda: f"E010 -> {db.equipos.find_one({'_id': 'E010'}, {'nombre': 1})['nombre']}")
    r.medir("lectura", "documento inexistente E999", contraste(lambda: db.equipos.find_one({"_id": "E999"}), None,
            "ausencia válida: la API responde 404"), tipo="contraste")
    r.medir("contexto", "database inexistente (fixture2030_x)", contraste(
        lambda: (cliente["fixture2030_x"].equipos.find_one(), "fixture2030_x" in cliente.list_database_names()), (None, False),
        "MongoDB no da error: un nombre de database mal escrito parece 'sin datos'"), tipo="contraste")


def neo4j(r: Registro):
    import httpx
    from neo4j import GraphDatabase
    from neo4j.exceptions import ClientError
    r.medir("protocolo", f"HTTP del Browser ({c['NEO4J_HTTP_URL']})", lambda: (
        lambda d: f"Neo4j {d['neo4j_version']} {d['neo4j_edition']}; el Browser responde, pero la API usa Bolt")(
            httpx.get(c["NEO4J_HTTP_URL"], timeout=T).json()))
    driver = GraphDatabase.driver(c["NEO4J_URI"], auth=(c["NEO4J_USUARIO"], c["NEO4J_PASSWORD"]),
                                  connection_timeout=T, max_transaction_retry_time=0)
    if not r.medir("protocolo", "Bolt (get_server_info)", lambda: (
            lambda i: f"{i.agent}, Bolt {i.protocol_version[0]}.{i.protocol_version[1]}")(driver.get_server_info())):
        return
    r.medir("autenticacion", f"usuario {c['NEO4J_USUARIO']}", lambda: (
        "credenciales aceptadas" if driver.verify_authentication() else fallar(PermissionError("credenciales rechazadas"))))
    otro = GraphDatabase.driver(c["NEO4J_URI"], auth=("diagnostico_inexistente", "x"), connection_timeout=T)
    r.medir("autenticacion", "usuario inexistente", contraste(otro.verify_authentication, False,
            "Bolt responde, pero rechaza la identidad"), tipo="contraste")
    r.medir("autorizacion", "SHOW CURRENT USER", lambda: (
        lambda rec: f"usuario {rec['user']}; roles {rec['roles']} (Community no tiene roles: todo usuario es administrador)")(
            driver.execute_query("SHOW CURRENT USER YIELD user, roles", database_="system").records[0]))
    r.medir("contexto", "database neo4j", lambda: f"RETURN 1 -> {driver.execute_query('RETURN 1 AS n', database_='neo4j').records[0]['n']}")
    r.medir("contexto", "database inexistente", contraste(
        lambda: driver.execute_query("RETURN 1", database_="fixture_inexistente"), ClientError,
        "Neo.ClientError.Database.DatabaseNotFound: la red y la identidad están bien"), tipo="contraste")
    leer = "MATCH (j:Jugador {id: $id}) RETURN j.id AS id LIMIT 1"
    r.medir("lectura", "Jugador E001-J09 (Cypher parametrizado)",
            lambda: f"{len(driver.execute_query(leer, id='E001-J09', database_='neo4j').records)} nodo")
    r.medir("lectura", "Jugador inexistente E999-J99", contraste(
        lambda: len(driver.execute_query(leer, id="E999-J99", database_="neo4j").records), 0,
        "resultado vacío: la API responde 404 PLAYER_NOT_FOUND"), tipo="contraste")
    driver.close()
    otro.close()


def cassandra(r: Registro):
    from cassandra import InvalidRequest
    from cassandra.cluster import Cluster, NoHostAvailable
    ks = c["CASSANDRA_KEYSPACE"]
    cluster = Cluster([c["CASSANDRA_HOST"]], port=int(c["CASSANDRA_PORT"]), connect_timeout=T)
    sesion = {}

    def conectar():
        sesion["s"] = cluster.connect()
        sesion["s"].default_timeout = T
        version = sesion["s"].execute("SELECT release_version FROM system.local").one().release_version
        return f"Cassandra {version}, protocolo CQL v{cluster.protocol_version}"
    if not r.medir("protocolo", "sesión CQL", conectar):
        return
    s = sesion["s"]
    r.anotar("autenticacion", "PasswordAuthenticator", "SKIP", "el laboratorio usa AllowAllAuthenticator (sin usuario)")
    r.anotar("autorizacion", "permisos sobre el keyspace", "SKIP", "sin autenticación no hay permisos que verificar")
    r.medir("contexto", f"keyspace {ks} y tabla comentarios_por_partido", lambda: "partición (" + ", ".join(
        f.column_name for f in sorted(s.execute(
            "SELECT column_name, position FROM system_schema.columns WHERE keyspace_name = %s "
            "AND table_name = 'comentarios_por_partido' AND kind = 'partition_key' ALLOW FILTERING", [ks]),
            key=lambda f: f.position)) + ")")
    def keyspace_inexistente():
        try:
            cluster.connect("ks_inexistente")
        except NoHostAvailable as e:
            if "keyspace" in str(e):
                return ("NoHostAvailable inmediato: el driver lo informa como si no hubiera hosts, pero el mensaje "
                        "nombra el keyspace (la causa es el contexto, no la red)")
            raise
        raise AssertionError("se conectó a un keyspace inexistente")
    r.medir("contexto", "keyspace inexistente", keyspace_inexistente, tipo="contraste")
    s.set_keyspace(ks)
    r.medir("lectura", "1 comentario de P001, bucket 20:00, shard 0", lambda: (
        lambda f: f"{f.comentario_id} ({f.creado_en:%Y-%m-%d %H:%M:%S})" if f else "partición vacía")(
            s.execute("SELECT comentario_id, creado_en FROM comentarios_por_partido WHERE partido_id = 'P001' "
                      "AND bucket_5m = '2030-06-08 20:00:00+0000' AND shard = 0 LIMIT 1").one()))
    r.medir("lectura", "consulta sin clave de partición", contraste(
        lambda: s.execute("SELECT comentario_id FROM comentarios_por_partido WHERE autor_id = 'U000042' LIMIT 1"),
        InvalidRequest, "consulta inválida: Cassandra la rechaza al instante, no es un timeout"), tipo="contraste")
    cluster.shutdown()
    otro = Cluster(["localhost"], port=7000, connect_timeout=T)
    r.medir("protocolo", "CQL contra localhost:7000", contraste(otro.connect, NoHostAvailable,
            "el TCP conecta, pero ese listener no habla CQL"), tipo="contraste")
    otro.shutdown()


def redis(r: Registro):
    import redis as redis_py
    from urllib.parse import urlsplit
    url = c["REDIS_URL"]
    cliente = redis_py.Redis.from_url(url, socket_timeout=T, socket_connect_timeout=T, decode_responses=True)
    if not r.medir("protocolo", "PING (RESP)", lambda: f"{'PONG' if cliente.ping() else '?'}, Redis {cliente.info('server')['redis_version']}"):
        return
    if not urlsplit(url).password:
        r.anotar("autenticacion", "AUTH", "SKIP", "la URL no tiene contraseña: el laboratorio corre sin requirepass")
    r.medir("autorizacion", "ACL WHOAMI", lambda: f"usuario {cliente.acl_whoami()} (sin ACL propias)")
    r.medir("contexto", "base lógica", lambda: f"db {cliente.connection_pool.connection_kwargs.get('db', 0)}, claves fixture2030:session:*")
    clave = "fixture2030:session:s-demo-001"

    def leer():
        if cliente.exists(clave):
            return f"{clave}: presente, TTL {cliente.ttl(clave)} s"
        return f"{clave}: ausente (TTL -2). Redis responde: la sesión expiró o no se creó (preparar_datos_demo.sh)"
    r.medir("lectura", "EXISTS y TTL de la sesión de prueba", leer)
    r.medir("lectura", "clave inexistente", contraste(
        lambda: (cliente.exists("fixture2030:session:s-no-existe"), cliente.ttl("fixture2030:session:s-no-existe")), (0, -2),
        "ausencia, no falla de Redis. Una clave expirada responde igual: Redis no las distingue"), tipo="contraste")


def influxdb(r: Registro):
    import httpx
    base, db, token = c["INFLUX_URL"], c["INFLUX_DATABASE"], c["INFLUX_TOKEN"]
    cliente = httpx.Client(base_url=base, timeout=T)

    def sql(q: str, base_logica: str = db, credencial: str = token):
        return cliente.post("/api/v3/query_sql", json={"db": base_logica, "q": q, "format": "json"},
                            headers={"Authorization": f"Bearer {credencial}"})

    def esperar(respuesta, codigo: int):
        if respuesta.status_code != codigo:
            raise AssertionError(f"HTTP {respuesta.status_code}")
        return respuesta

    if not r.medir("protocolo", "GET /health (sin token)", lambda: f"HTTP {esperar(cliente.get('/health'), 200).status_code} {cliente.get('/health').text.strip()}"):
        return
    r.medir("autenticacion", "token de .env", lambda: f"SELECT 1 -> HTTP {esperar(sql('SELECT 1'), 200).status_code}")
    r.medir("autenticacion", "token inválido", contraste(lambda: sql("SELECT 1", credencial="apiv3_invalido").status_code, 401,
            "el servicio responde, pero no autoriza"), tipo="contraste")
    r.medir("autorizacion", "listar databases (requiere token de administrador)", lambda: (
        lambda filas: f"{len(filas)} databases visibles")(esperar(cliente.get(
            "/api/v3/configure/database", params={"format": "json"}, headers={"Authorization": f"Bearer {token}"}), 200).json()))
    r.medir("contexto", f"database {db}", lambda: f"SELECT 1 en {db} -> HTTP {esperar(sql('SELECT 1'), 200).status_code}")
    r.medir("contexto", "database inexistente", contraste(lambda: sql("SELECT 1", "no_existe").status_code, 404,
            "token válido, contexto equivocado"), tipo="contraste")
    ventana = ("SELECT count(*) AS n FROM estadisticas_equipo WHERE partido_id = 'P001' "
               "AND time >= '{}T16:00:00Z' AND time < '{}T16:00:02Z'")
    r.medir("lectura", "P001, ventana de 2 s (raw)", lambda: f"{esperar(sql(ventana.format('2030-06-08', '2030-06-08')), 200).json()[0]['n']} puntos")
    r.medir("lectura", "ventana sin puntos (2031)", contraste(
        lambda: esperar(sql(ventana.format("2031-06-08", "2031-06-08")), 200).json()[0]["n"], 0,
        "HTTP 200 con 0 puntos: ausencia de datos, no error"), tipo="contraste")


def iris(r: Registro):
    import httpx
    import iris as iris_py
    host, puerto, ns = c["IRIS_HOST"], int(c["IRIS_PORT"]), c["IRIS_NAMESPACE"]
    r.medir("protocolo", "portal HTTP (Management Portal)", lambda: (
        f"HTTP {httpx.get(c['IRIS_PORTAL_URL'] + '/csp/sys/UtilHome.csp', timeout=T).status_code}: "
        "el portal responde, pero la API usa el Superserver"))
    conexion = {}

    def conectar():
        conexion["c"] = iris_py.connect(host, puerto, ns, c["IRIS_USUARIO"], c["IRIS_PASSWORD"], timeout=MS)
        return f"{c['IRIS_USUARIO']} conectado al Superserver (el driver hace handshake y login en una sola operación)"
    if not r.medir("autenticacion", f"usuario {c['IRIS_USUARIO']} en {ns}", conectar):
        return
    nativo, cursor = iris_py.createIRIS(conexion["c"]), conexion["c"].cursor()
    r.medir("protocolo", "versión (API nativa)", lambda: str(nativo.classMethodValue("%SYSTEM.Version", "GetVersion"))[:60])
    r.medir("autenticacion", "usuario inexistente", contraste(
        lambda: iris_py.connect(host, puerto, ns, "diagnostico_inexistente", "x", timeout=MS), RuntimeError,
        "Access Denied"), tipo="contraste")
    r.medir("autorizacion", "permiso READ sobre %DB_USER", lambda: (
        "permitido" if str(nativo.classMethodValue("%SYSTEM.Security", "Check", "%DB_USER", "READ")) == "1"
        else fallar(PermissionError("sin permiso de lectura"))))
    def uno(sql: str, *parametros):
        cursor.execute(sql, list(parametros))
        return cursor.fetchone()

    r.medir("contexto", f"namespace {ns} y clase Fixture.Partido", lambda: (
        f"namespace activo {nativo.classMethodValue('%SYSTEM.SYS', 'NameSpace')}, clase compilada: "
        f"{uno('SELECT COUNT(*) FROM %Dictionary.CompiledClass WHERE Name = ?', 'Fixture.Partido')[0]}"))
    r.medir("contexto", "namespace inexistente", contraste(
        lambda: (nativo.classMethodValue("%SYS.Namespace", "Exists", "NOEXISTE"),
                 _rechaza(lambda: iris_py.connect(host, puerto, "NOEXISTE", c["IRIS_USUARIO"], c["IRIS_PASSWORD"], timeout=MS))),
        (0, "Access Denied"),
        "Exists() lo detecta; al conectar, IRIS responde el mismo Access Denied que con un usuario inválido"),
        tipo="contraste")
    leer = "SELECT Codigo, Estado FROM Fixture.Partido WHERE Codigo = ?"
    r.medir("lectura", "Fixture.Partido P001", lambda: " ".join(map(str, uno(leer, "P001"))))
    r.medir("lectura", "partido inexistente P999", contraste(lambda: uno(leer, "P999"), None,
            "objeto inexistente: la API responde 404 MATCH_NOT_FOUND"), tipo="contraste")
    conexion["c"].close()


def _rechaza(funcion) -> str:
    try:
        funcion()
    except RuntimeError as e:
        return "Access Denied" if "Access Denied" in str(e) else str(e)[:60]
    return "conectó"


def clis(r: Registro, producto: str):
    """El CLI nativo en la notebook es opcional: SKIP no significa producto caído."""
    ruta = shutil.which(CLIS[producto])
    if ruta:
        r.anotar("protocolo", f"CLI {CLIS[producto]}", "OK", f"instalado en {mostrar('', ruta)}")
    else:
        r.anotar("protocolo", f"CLI {CLIS[producto]}", "SKIP",
                 "no instalado en la notebook (está dentro del contenedor, que es otro origen); se usa el driver de la API")


PRODUCTOS = {"mongodb": mongodb, "neo4j": neo4j, "cassandra": cassandra, "redis": redis, "influxdb": influxdb, "iris": iris}

for producto in sys.argv[1:] or PRODUCTOS:
    registro = Registro(producto)
    clis(registro, producto)
    try:
        PRODUCTOS[producto](registro)
    except Exception as e:  # una falla inesperada de un producto no frena a los demás (RNF13)
        registro.anotar("protocolo", "prueba del producto", "FALLA", f"{type(e).__name__}: {mostrar('', str(e))[:120]}")
