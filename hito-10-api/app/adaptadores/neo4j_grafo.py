"""Adaptador de Neo4j (Hito 5): recorridos de relaciones. Cypher siempre parametrizado.

Recorrido: (Jugador)-[:PARTICIPA_EN]->(Partido)<-[:DISPUTA]-(rival:Equipo), excluyendo el equipo
propio del jugador. Es una consulta de relaciones: en MongoDB serían varios $lookup encadenados.
"""
from neo4j import GraphDatabase, RoutingControl
from neo4j.exceptions import AuthError, ServiceUnavailable, SessionExpired

from app.adaptadores.limite import con_limite
from app.config import config
from app.errores import DependenciaNoDisponible, DependenciaTimeout, NoEncontrado

MAX_PARTIDOS = 200  # tope del recorrido: un jugador juega a lo sumo 8 partidos en el torneo
_driver = GraphDatabase.driver(config.neo4j_uri, auth=(config.neo4j_usuario, config.neo4j_password),
                               connection_timeout=config.timeout_s, connection_acquisition_timeout=config.timeout_s,
                               # Por defecto el driver reintenta 30 s ante una base caída. Con un solo nodo
                               # el reintento no aporta: se desactiva para que el 503 llegue dentro del timeout.
                               max_transaction_retry_time=0)

_ERRORES = (ServiceUnavailable, SessionExpired, AuthError)

_PARTIDOS_DE_JUGADOR = """
MATCH (j:Jugador {id: $codigo})
OPTIONAL MATCH (j)-[r:PARTICIPA_EN]->(p:Partido)
OPTIONAL MATCH (rival:Equipo)-[:DISPUTA]->(p) WHERE NOT (j)-[:PERTENECE_A]->(rival)
WITH j, r, p, rival ORDER BY p.fecha, p.id LIMIT $limite
RETURN j.id AS jugador,
       collect(CASE WHEN p IS NOT NULL THEN {partidoCodigo: p.id, fecha: toString(p.fecha), fase: p.fase,
                                             titular: r.titular, rivalCodigo: rival.id} END) AS partidos
"""


def _no_disponible(e: Exception):
    # Si la base acepta TCP pero no contesta, el driver informa el handshake Bolt sin respuesta como
    # ServiceUnavailable: es un timeout, no un rechazo (con la base detenida, el mensaje es "refused").
    if isinstance(e, ServiceUnavailable) and "handshake" in str(e):
        return DependenciaTimeout("Neo4j", "ServiceUnavailable (handshake Bolt sin respuesta)")
    return DependenciaNoDisponible("Neo4j", type(e).__name__)


def partidos_de_jugador(codigo: str) -> list[dict]:
    try:
        # timeout limita la transacción en el servidor; con_limite, la espera del cliente (el driver no la limita).
        registros, _, _ = con_limite("Neo4j", _driver.execute_query, _PARTIDOS_DE_JUGADOR, codigo=codigo,
                                     limite=MAX_PARTIDOS, routing_=RoutingControl.READ, timeout=config.timeout_s)
    except _ERRORES as e:
        raise _no_disponible(e)
    if not registros:
        raise NoEncontrado(f"No existe el jugador {codigo}", "PLAYER_NOT_FOUND")
    return registros[0]["partidos"]


def ping() -> None:
    try:
        con_limite("Neo4j", _driver.execute_query, "RETURN 1", routing_=RoutingControl.READ, timeout=config.timeout_s)
    except _ERRORES as e:
        raise _no_disponible(e)
