"""Adaptador de Neo4j (Hito 5): eventos conectados con un partido. Cypher siempre parametrizado."""
import logging

from neo4j import GraphDatabase, RoutingControl
from neo4j.exceptions import AuthError, ServiceUnavailable, SessionExpired

from app.config import config
from app.errores import DependenciaNoDisponible, NoEncontrado

log = logging.getLogger("api.neo4j")
MAX_EVENTOS = 200  # tope del recorrido: un partido real tiene decenas de eventos
_driver = GraphDatabase.driver(config.neo4j_uri, auth=(config.neo4j_usuario, config.neo4j_password),
                               connection_timeout=config.timeout_s, connection_acquisition_timeout=config.timeout_s,
                               # Por defecto el driver reintenta 30 s ante una base caída. Con un solo nodo
                               # el reintento no aporta: se desactiva para que el 503 llegue dentro del timeout.
                               max_transaction_retry_time=0)

_EVENTOS = """
MATCH (p:Partido {id: $codigo})
OPTIONAL MATCH (e:Evento)-[:OCURRE_EN]->(p)
OPTIONAL MATCH (j:Jugador)-[:PROTAGONIZA]->(e)
WITH p, e, j ORDER BY e.minuto LIMIT $limite
RETURN p.id AS partido,
       collect(CASE WHEN e IS NOT NULL THEN {tipo: e.tipo, minuto: e.minuto, jugadorCodigo: j.id} END) AS eventos
"""


def eventos_de_partido(codigo: str) -> list[dict]:
    try:
        registros, _, _ = _driver.execute_query(_EVENTOS, codigo=codigo, limite=MAX_EVENTOS,
                                                routing_=RoutingControl.READ,
                                                timeout=config.timeout_s)
    except (ServiceUnavailable, SessionExpired, AuthError) as e:
        log.warning("Neo4j no disponible: %s", type(e).__name__)
        raise DependenciaNoDisponible("Neo4j")
    if not registros:
        raise NoEncontrado(f"No existe el partido {codigo}", "MATCH_NOT_FOUND")
    return registros[0]["eventos"]
