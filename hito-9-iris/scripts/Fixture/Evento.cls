/// Evento de un partido (gol, tarjeta, cambio). Hijo de Partido (RF3): no existe sin su partido.
Class Fixture.Evento Extends %Persistent
{

Relationship Partido As Fixture.Partido [ Cardinality = parent, Inverse = Eventos ];

Property Tipo As %String [ Required ];

Property Minuto As %Integer [ Required ];

Property Jugador As Fixture.Jugador [ Required ];

/// RNF3: índice sobre la propiedad relacional del lado hijo.
Index PartidoIdx On Partido;

}
