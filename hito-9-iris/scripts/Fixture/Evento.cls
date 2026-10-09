/// Evento de un partido (gol, tarjeta, sustitución). Hijo de Partido (relación
/// padre-hijo, RF3): no existe sin su partido y se borra con él.
Class Fixture.Evento Extends %Persistent
{

Relationship Partido As Fixture.Partido [ Cardinality = parent, Inverse = Eventos ];

Property Tipo As %String(VALUELIST = ",GOL,TARJETA_AMARILLA,TARJETA_ROJA,SUSTITUCION") [ Required ];

/// Minuto de juego: no existe el minuto 0.
Property Minuto As %Integer(MAXVAL = 130, MINVAL = 1) [ Required ];

Property Jugador As Fixture.Jugador [ Required ];

/// RNF3: índice sobre la propiedad relacional del lado hijo (recomendado en la Clase 10).
Index PartidoIdx On Partido;

}
