// Subgrafo acotado para Neo4j Browser.
MATCH (e:Equipo {id: 'E001'})<-[:PERTENECE_A]-(j:Jugador)
WITH e, collect(j)[0..5] AS jugadores
MATCH (e)-[:DISPUTA]->(p:Partido)-[:SE_JUEGA_EN]->(s:Sede)
WITH e, jugadores, collect(DISTINCT p)[0..3] AS partidos, collect(DISTINCT s)[0..3] AS sedes
UNWIND jugadores AS j
UNWIND partidos AS p
OPTIONAL MATCH (j)-[part:PARTICIPA_EN]->(p)
OPTIONAL MATCH (j)-[:PROTAGONIZA]->(ev:Evento)-[:OCURRE_EN]->(p)
RETURN e, j, p, sedes, part, ev
LIMIT 80;
