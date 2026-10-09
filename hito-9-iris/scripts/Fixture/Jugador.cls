/// Jugador de una selección (RF4: hereda de Persona).
/// Lado "muchos" de la relación Equipo -> Jugadores (RF3).
Class Fixture.Jugador Extends Fixture.Persona
{

/// Código de los hitos anteriores: <equipo>Jnn (ej. E001J09).
Property Codigo As %String(MAXLEN = 7) [ Required ];

Property Dorsal As %Integer(MAXVAL = 99, MINVAL = 1) [ Required ];

Property Posicion As %String(VALUELIST = ",ARQ,DEF,MED,DEL") [ Required ];

/// Si se borra el equipo, el jugador sigue existiendo sin equipo.
Relationship Equipo As Fixture.Equipo [ Cardinality = one, Inverse = Jugadores, OnDelete = setnull ];

/// RNF3: índice sobre la propiedad relacional del lado "muchos".
Index EquipoIdx On Equipo;

}
