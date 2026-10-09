/// Partido del Fixture 2030: PROGRAMADO -> EN_JUEGO -> FINALIZADO.
/// Padre de sus eventos (relación padre-hijo, RF3): los eventos se guardan con el
/// partido en un solo %Save (RF6) y se borran con él.
/// Los cambios de estado y el registro de eventos se hacen con los métodos de la clase,
/// que son la interfaz de escritura autorizada (RF9).
Class Fixture.Partido Extends %Persistent
{

Property Codigo As %String(MAXLEN = 4) [ Required ];

Property FechaHora As %TimeStamp [ Required ];

Property Estado As %String(VALUELIST = ",PROGRAMADO,EN_JUEGO,FINALIZADO") [ InitialExpression = "PROGRAMADO", Required ];

Property Sede As Fixture.Sede [ Required ];

Property EquipoLocal As Fixture.Equipo [ Required ];

Property EquipoVisitante As Fixture.Equipo [ Required ];

Property Arbitro As Fixture.Arbitro [ Required ];

Relationship Eventos As Fixture.Evento [ Cardinality = children, Inverse = Partido ];

/// Búsqueda por código de partido.
Index CodigoIdx On Codigo [ Unique ];

/// PROGRAMADO -> EN_JUEGO.
Method Iniciar() As %Status
{
    if ..Estado '= "PROGRAMADO" {
        quit $$$ERROR($$$GeneralError, "Transición ilegal: "_..Estado_" -> EN_JUEGO")
    }
    set ..Estado = "EN_JUEGO"
    quit $$$OK
}

/// EN_JUEGO -> FINALIZADO.
Method Finalizar() As %Status
{
    if ..Estado '= "EN_JUEGO" {
        quit $$$ERROR($$$GeneralError, "Transición ilegal: "_..Estado_" -> FINALIZADO")
    }
    set ..Estado = "FINALIZADO"
    quit $$$OK
}

/// Agrega un evento al partido en memoria; se guarda con el próximo %Save del partido.
/// Regla (RF9): solo un partido EN_JUEGO admite eventos.
Method RegistrarEvento(tipo As %String, minuto As %Integer, jugador As Fixture.Jugador) As %Status
{
    if ..Estado '= "EN_JUEGO" {
        quit $$$ERROR($$$GeneralError, "No se pueden registrar eventos: el partido "_..Codigo_" está "_..Estado)
    }
    set evento = ##class(Fixture.Evento).%New()
    set evento.Tipo = tipo
    set evento.Minuto = minuto
    set evento.Jugador = jugador
    do ..Eventos.Insert(evento)
    quit $$$OK
}

/// Valida el objeto completo antes de guardarlo.
Method %OnBeforeSave(insert As %Boolean) As %Status [ Private, ServerOnly = 1 ]
{
    if ..EquipoLocal = ..EquipoVisitante {
        quit $$$ERROR($$$GeneralError, "Un equipo no puede jugar contra sí mismo")
    }
    quit $$$OK
}

}
