// Conteos principales.
MATCH (e:Equipo)
WITH count(e) AS equipos
MATCH (j:Jugador)
WITH equipos, count(j) AS jugadores
MATCH (p:Partido)
WITH equipos, jugadores, count(p) AS partidos
MATCH (s:Sede)
WITH equipos, jugadores, partidos, count(s) AS sedes
MATCH (ev:Evento)
WITH equipos, jugadores, partidos, sedes, count(ev) AS eventos
MATCH ()-[r:PARTICIPA_EN]->()
RETURN equipos,
       jugadores,
       partidos,
       sedes,
       eventos,
       count(r) AS participaciones;

// Jugadores sin equipo: esperado 0.
MATCH (j:Jugador)
WHERE NOT (j)-[:PERTENECE_A]->(:Equipo)
RETURN count(j) AS jugadoresSinEquipo;

// Partidos que no tengan exactamente dos equipos: esperado 0.
MATCH (p:Partido)
OPTIONAL MATCH (:Equipo)-[:DISPUTA]->(p)
WITH p, count(*) AS cantidadEquipos
WHERE cantidadEquipos <> 2
RETURN count(p) AS partidosConCantidadInvalidaDeEquipos;

// Partidos sin sede: esperado 0.
MATCH (p:Partido)
WHERE NOT (p)-[:SE_JUEGA_EN]->(:Sede)
RETURN count(p) AS partidosSinSede;

// Eventos sin partido: esperado 0.
MATCH (ev:Evento)
WHERE NOT (ev)-[:OCURRE_EN]->(:Partido)
RETURN count(ev) AS eventosSinPartido;

// Eventos sin protagonista: esperado 0.
MATCH (ev:Evento)
WHERE NOT (:Jugador)-[:PROTAGONIZA]->(ev)
RETURN count(ev) AS eventosSinProtagonista;

// Participaciones duplicadas entre un mismo jugador y partido: esperado 0.
MATCH (j:Jugador)-[r:PARTICIPA_EN]->(p:Partido)
WITH j, p, count(r) AS cantidad
WHERE cantidad > 1
RETURN count(*) AS participacionesDuplicadas;

// Jugadores participando en un partido que su equipo no disputa: esperado 0.
MATCH (j:Jugador)-[:PERTENECE_A]->(e:Equipo)
MATCH (j)-[:PARTICIPA_EN]->(p:Partido)
WHERE NOT (e)-[:DISPUTA]->(p)
RETURN count(*) AS participacionesIncoherentes;
