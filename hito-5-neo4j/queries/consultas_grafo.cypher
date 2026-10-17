// Q1 — Equipos del Grupo A.
// Grupo es propiedad de Equipo porque el uso es de clasificación/filtro.
MATCH (e:Equipo)
WHERE e.grupo = 'A'
RETURN e.id AS equipoId,
       e.nombre AS equipo,
       e.grupo AS grupo
ORDER BY equipoId;

// Q2 — Partidos de una fase.
// Fase es propiedad de Partido.
MATCH (p:Partido)
WHERE p.fase = 'Cuartos'
RETURN p.id AS partido,
       p.fecha AS fecha,
       p.estado AS estado
ORDER BY fecha;

// Q3 — Recorrido de 3 relaciones:
// Jugador -> Equipo -> Partido -> Sede.
MATCH (j:Jugador {id: 'E001-J10'})
      -[:PERTENECE_A]->(e:Equipo)
      -[:DISPUTA]->(p:Partido)
      -[:SE_JUEGA_EN]->(s:Sede)
RETURN j.id AS jugador,
       e.nombre AS equipo,
       p.id AS partido,
       p.fase AS fase,
       p.fecha AS fecha,
       s.nombre AS sede
ORDER BY fecha;

// Q4 — Participación efectiva:
// Jugador -> Partido -> Sede.
MATCH (j:Jugador {id: 'E001-J10'})
      -[r:PARTICIPA_EN]->(p:Partido)
      -[:SE_JUEGA_EN]->(s:Sede)
RETURN j.id AS jugador,
       p.id AS partido,
       r.titular AS titular,
       p.fase AS fase,
       s.nombre AS sede
ORDER BY p.fecha;

// Q5 — Jugadores que efectivamente participaron contra E002.
// Equipo -> Partido <- Jugador, más pertenencia para identificar el rival.
MATCH (rival:Equipo {id: 'E002'})-[:DISPUTA]->(p:Partido)
MATCH (j:Jugador)-[part:PARTICIPA_EN]->(p)
MATCH (j)-[:PERTENECE_A]->(e:Equipo)
WHERE e.id <> rival.id
RETURN DISTINCT j.id AS jugador,
       e.id AS equipo,
       p.id AS partido,
       part.titular AS titular
ORDER BY partido, equipo, jugador;

// Q6 — Recorrido de 3 relaciones:
// Jugador -> Evento -> Partido -> Sede.
MATCH (j:Jugador)
      -[:PROTAGONIZA]->(ev:Evento)
      -[:OCURRE_EN]->(p:Partido)
      -[:SE_JUEGA_EN]->(s:Sede)
WHERE ev.tipo = 'Gol'
RETURN j.id AS jugador,
       ev.id AS evento,
       ev.minuto AS minuto,
       p.id AS partido,
       p.fase AS fase,
       s.nombre AS sede
ORDER BY p.fecha, ev.minuto
LIMIT 25;

// Q7 — Rivales de E001 mediante el partido compartido.
MATCH (e:Equipo {id: 'E001'})-[:DISPUTA]->(p:Partido)<-[:DISPUTA]-(rival:Equipo)
WHERE rival.id <> e.id
RETURN p.id AS partido,
       p.fecha AS fecha,
       rival.id AS rivalId,
       rival.nombre AS rival
ORDER BY fecha;
