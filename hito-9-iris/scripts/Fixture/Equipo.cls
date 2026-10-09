/// Selección participante. Lado "uno" de la relación Equipo -> Jugadores (RF3).
Class Fixture.Equipo Extends %Persistent
{

/// Código de los hitos anteriores (E001...).
Property Codigo As %String(MAXLEN = 4) [ Required ];

Property Nombre As %String(MAXLEN = 60) [ Required ];

Property Confederacion As %String(VALUELIST = ",AFC,CAF,CONCACAF,CONMEBOL,OFC,UEFA") [ Required ];

Relationship Jugadores As Fixture.Jugador [ Cardinality = many, Inverse = Equipo ];

}
