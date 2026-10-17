// A1 — Camino más corto entre dos equipos a través de partidos.
// DISPUTA tiene dirección semántica Equipo -> Partido, pero la conectividad
// se analiza recorriéndola en ambos sentidos.
MATCH (origen:Equipo {id: 'E001'}),
      (destino:Equipo {id: 'E032'})
MATCH camino = shortestPath((origen)-[:DISPUTA*..20]-(destino))
RETURN length(camino) AS cantidadRelaciones,
       [n IN nodes(camino) | coalesce(n.id, '')] AS recorrido;

// A2 — Conectividad simple: cantidad de rivales distintos por equipo.
MATCH (e:Equipo)-[:DISPUTA]->(p:Partido)<-[:DISPUTA]-(rival:Equipo)
WHERE rival.id <> e.id
WITH e, count(DISTINCT rival) AS rivalesDistintos
RETURN e.id AS equipoId,
       e.nombre AS equipo,
       e.grupo AS grupo,
       rivalesDistintos
ORDER BY rivalesDistintos DESC, equipoId
LIMIT 10;
