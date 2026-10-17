// EQUIPOS
LOAD CSV WITH HEADERS FROM 'file:///equipos.csv' AS row
MERGE (e:Equipo {id: row.id})
SET e.nombre = row.nombre,
    e.pais = row.pais,
    e.confederacion = row.confederacion,
    e.grupo = row.grupo;

// JUGADORES + PERTENENCIA
LOAD CSV WITH HEADERS FROM 'file:///jugadores.csv' AS row
MATCH (e:Equipo {id: row.equipo_id})
MERGE (j:Jugador {id: row.id})
SET j.nombre = row.nombre,
    j.apellido = row.apellido,
    j.fechaNacimiento = date(row.fecha_nacimiento),
    j.nacionalidad = row.nacionalidad,
    j.posicion = row.posicion,
    j.dorsal = toInteger(row.dorsal)
MERGE (j)-[:PERTENECE_A]->(e);

// SEDES
LOAD CSV WITH HEADERS FROM 'file:///sedes.csv' AS row
MERGE (s:Sede {id: row.id})
SET s.nombre = row.nombre,
    s.ciudad = row.ciudad,
    s.pais = row.pais;

// PARTIDOS + EQUIPOS + SEDE
LOAD CSV WITH HEADERS FROM 'file:///partidos.csv' AS row
MATCH (local:Equipo {id: row.local_id})
MATCH (visitante:Equipo {id: row.visitante_id})
MATCH (s:Sede {id: row.sede_id})
MERGE (p:Partido {id: row.id})
SET p.fecha = date(row.fecha),
    p.fase = row.fase,
    p.jornada = toInteger(row.jornada),
    p.estado = row.estado
MERGE (local)-[rl:DISPUTA]->(p)
SET rl.rol = 'local'
MERGE (visitante)-[rv:DISPUTA]->(p)
SET rv.rol = 'visitante'
MERGE (p)-[:SE_JUEGA_EN]->(s);

// PARTICIPACIÓN REAL.
// titular es una propiedad contextual de la relación, no una estadística acumulada.
LOAD CSV WITH HEADERS FROM 'file:///participaciones.csv' AS row
MATCH (j:Jugador {id: row.jugador_id})
MATCH (p:Partido {id: row.partido_id})
MERGE (j)-[r:PARTICIPA_EN]->(p)
SET r.titular = toBoolean(row.titular);

// EVENTOS
LOAD CSV WITH HEADERS FROM 'file:///eventos.csv' AS row
MATCH (j:Jugador {id: row.jugador_id})
MATCH (p:Partido {id: row.partido_id})
MERGE (ev:Evento {id: row.id})
SET ev.tipo = row.tipo,
    ev.minuto = toInteger(row.minuto),
    ev.descripcion = row.descripcion
MERGE (j)-[:PROTAGONIZA]->(ev)
MERGE (ev)-[:OCURRE_EN]->(p);
