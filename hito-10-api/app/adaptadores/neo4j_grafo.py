"""Adaptador de Neo4j (Hito 5): recorridos de relaciones. Cypher siempre parametrizado.

Recorrido: (Jugador)-[:PARTICIPA_EN]->(Partido)<-[:DISPUTA]-(rival:Equipo), excluyendo el equipo
propio del jugador. Es una consulta de relaciones: en MongoDB serían varios $lookup encadenados.
"""
import logging

from neo4j import GraphDatabase, RoutingControl
from neo4j.exceptions import AuthError, ServiceUnavailable, SessionExpired

from app.config import config
from app.errores import DependenciaNoDisponible, NoEncontrado

log = logging.getLogger("api.neo4j")
MAX_PARTIDOS = 200  # tope del recorrido: un jugador juega a lo sumo 8 partidos en el torneo
_driver = GraphDatabase.driver(config.neo4j_uri, auth=(config.neo4j_usuario, config.neo4j_password),
                               connection_timeout=config.timeout_s, connection_acquisition_timeout=config.timeout_s,
                               # Por defecto el driver reintenta 30 s ante una base caída. Con un solo nodo
                               # el reintento no aporta: se desactiva para que el 503 llegue dentro del timeout.
                               max_transaction_retry_time=0)

_PARTIDOS_DE_JUGADOR = """
MATCH (j:Jugador {id: $codigo})
OPTIONAL MATCH (j)-[r:PARTICIPA_EN]->(p:Partido)
OPTIONAL MATCH (rival:Equipo)-[:DISPUTA]->(p) WHERE NOT (j)-[:PERTENECE_A]->(rival)
WITH j, r, p, rival ORDER BY p.fecha, p.id LIMIT $limite
RETURN j.id AS jugador,
       collect(CASE WHEN p IS NOT NULL THEN {partidoCodigo: p.id, fecha: toString(p.fecha), fase: p.fase,
                                             titular: r.titular, rivalCodigo: rival.id} END) AS partidos
"""


def partidos_de_jugador(codigo: str) -> list[dict]:
    try:
        registros, _, _ = _driver.execute_query(_PARTIDOS_DE_JUGADOR, codigo=codigo, limite=MAX_PARTIDOS,
                                                routing_=RoutingControl.READ, timeout=config.timeout_s)
    except (ServiceUnavailable, SessionExpired, AuthError) as e:
        log.warning("Neo4j no disponible: %s", type(e).__name__)
        raise DependenciaNoDisponible("Neo4j")
    if not registros:
        raise NoEncontrado(f"No existe el jugador {codigo}", "PLAYER_NOT_FOUND")
    return registros[0]["partidos"]
