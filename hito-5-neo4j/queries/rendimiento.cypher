// Los PROFILE deben ejecutarse individualmente en Neo4j Browser o cypher-shell
// para registrar el plan real.

// R1 — filtro frecuente por grupo.
PROFILE
MATCH (e:Equipo)
WHERE e.grupo = 'A'
RETURN e.id, e.nombre;

// R2 — filtro frecuente por fase.
PROFILE
MATCH (p:Partido)
WHERE p.fase = 'Cuartos'
RETURN p.id, p.fecha;

// R3 — filtro frecuente por tipo de evento.
PROFILE
MATCH (ev:Evento)
WHERE ev.tipo = 'Gol'
RETURN ev.id, ev.minuto
LIMIT 25;
