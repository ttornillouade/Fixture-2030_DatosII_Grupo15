/// Partido del Fixture 2030. Padre de sus eventos (RF3: relación padre-hijo): los eventos se
/// guardan con el partido en un solo %Save (RF6) y se borran con él.
Class Fixture.Partido Extends %Persistent
{

Property Codigo As %String [ Required ];

Property Estado As %String [ InitialExpression = "PROGRAMADO", Required ];

Relationship Eventos As Fixture.Evento [ Cardinality = children, Inverse = Partido ];

/// RF9: validación encapsulada. Un partido FINALIZADO no admite eventos nuevos.
Method RegistrarEvento(tipo As %String, minuto As %Integer, jugador As Fixture.Jugador) As %Status
{
    if ..Estado = "FINALIZADO" {
        quit $$$ERROR($$$GeneralError, "No se pueden registrar eventos: el partido "_..Codigo_" está FINALIZADO")
    }
    set evento = ##class(Fixture.Evento).%New()
    set evento.Tipo = tipo
    set evento.Minuto = minuto
    set evento.Jugador = jugador
    do ..Eventos.Insert(evento)
    quit $$$OK
}

}
