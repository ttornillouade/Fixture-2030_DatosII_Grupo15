// CREATE controlado: evento de prueba.
MATCH (j:Jugador {id: 'E001-J01'})
MATCH (p:Partido {id: 'P001'})
MERGE (ev:Evento {id: 'EV-DEMO'})
SET ev.tipo = 'TarjetaAmarilla',
    ev.minuto = 15,
    ev.descripcion = 'Evento temporal para demostrar CRUD'
MERGE (j)-[:PROTAGONIZA]->(ev)
MERGE (ev)-[:OCURRE_EN]->(p);

// READ
MATCH (j:Jugador)-[:PROTAGONIZA]->(ev:Evento {id: 'EV-DEMO'})-[:OCURRE_EN]->(p:Partido)
RETURN j.id AS jugador,
       ev.id AS evento,
       ev.tipo AS tipo,
       ev.minuto AS minuto,
       p.id AS partido;

// UPDATE
MATCH (ev:Evento {id: 'EV-DEMO'})
SET ev.minuto = 18,
    ev.descripcion = 'Evento temporal actualizado'
RETURN ev.id AS evento,
       ev.minuto AS minuto,
       ev.descripcion AS descripcion;

// DELETE acotado al nodo de prueba.
MATCH (ev:Evento {id: 'EV-DEMO'})
DETACH DELETE ev;
