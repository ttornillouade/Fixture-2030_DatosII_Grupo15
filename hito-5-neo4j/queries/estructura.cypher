// Restricciones de unicidad.
// Cada entidad tiene un identificador estable y compartido entre módulos cuando corresponde.
CREATE CONSTRAINT equipo_id_unique IF NOT EXISTS
FOR (e:Equipo)
REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT jugador_id_unique IF NOT EXISTS
FOR (j:Jugador)
REQUIRE j.id IS UNIQUE;

CREATE CONSTRAINT partido_id_unique IF NOT EXISTS
FOR (p:Partido)
REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT sede_id_unique IF NOT EXISTS
FOR (s:Sede)
REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT evento_id_unique IF NOT EXISTS
FOR (ev:Evento)
REQUIRE ev.id IS UNIQUE;

// Índices para filtros frecuentes del módulo.
CREATE INDEX equipo_grupo IF NOT EXISTS
FOR (e:Equipo)
ON (e.grupo);

CREATE INDEX jugador_posicion IF NOT EXISTS
FOR (j:Jugador)
ON (j.posicion);

CREATE INDEX partido_fase IF NOT EXISTS
FOR (p:Partido)
ON (p.fase);

CREATE INDEX partido_fecha IF NOT EXISTS
FOR (p:Partido)
ON (p.fecha);

CREATE INDEX evento_tipo IF NOT EXISTS
FOR (ev:Evento)
ON (ev.tipo);
