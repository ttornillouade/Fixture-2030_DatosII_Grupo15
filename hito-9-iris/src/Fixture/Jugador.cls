/// Jugador de un plantel (RF4: hereda de Persona).
/// Lado "muchos" de la relación Equipo -> Jugadores (RF3).
Class Fixture.Jugador Extends Fixture.Persona
{

/// Código del jugador en los hitos anteriores: <equipo>Jnn (ej. E001J09).
Property Codigo As %String(MAXLEN = 7, PATTERN = "1""E""3N1""J""2N") [ Required ];

Property Dorsal As %Integer(MAXVAL = 99, MINVAL = 1) [ Required ];

Property Posicion As %String(DISPLAYLIST = ",Arquero,Defensor,Mediocampista,Delantero", VALUELIST = ",ARQ,DEF,MED,DEL") [ Required ];

/// Relación bidireccional con el equipo. OnDelete = noaction: no se puede borrar
/// un equipo que todavía tiene jugadores.
Relationship Equipo As Fixture.Equipo [ Cardinality = one, Inverse = Jugadores, OnDelete = noaction, Required ];

Index CodigoIdx On Codigo [ Unique ];

/// RNF3: índice sobre la propiedad relacional del lado "muchos". IRIS lo usa para
/// cargar Equipo.Jugadores sin recorrer toda la tabla.
Index EquipoIdx On Equipo;

/// Un dorsal no se repite dentro del mismo equipo.
Index EquipoDorsalIdx On (Equipo, Dorsal) [ Unique ];

}
