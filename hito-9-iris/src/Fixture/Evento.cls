/// Evento de un partido (gol, tarjeta, sustitución). Hijo de Partido (parent/children, RF3):
/// se guarda dentro del partido y no existe sin él.
/// Un evento registrado es inalterable: no se modifica ni por objetos ni por SQL.
Class Fixture.Evento Extends %Persistent
{

Relationship Partido As Fixture.Partido [ Cardinality = parent, Inverse = Eventos ];

Property Tipo As %String(VALUELIST = ",GOL,TARJETA_AMARILLA,TARJETA_ROJA,SUSTITUCION") [ Required ];

/// Minuto de juego. 0 no existe; hasta 130 cubre alargue y tiempo adicionado.
Property Minuto As %Integer(MAXVAL = 130, MINVAL = 1) [ Required ];

Property Jugador As Fixture.Jugador [ Required ];

/// Equipo del jugador al momento del evento (se guarda para no depender de transferencias futuras).
Property Equipo As Fixture.Equipo [ Required ];

Property RegistradoEn As %TimeStamp [ InitialExpression = {$ZDATETIME($ZTIMESTAMP, 3)}, Required ];

/// RNF3: índice sobre la propiedad relacional del lado "muchos".
Index PartidoIdx On Partido;

/// Para consultas por jugador (goleadores, tarjetas).
Index JugadorIdx On Jugador;

ForeignKey JugadorFK(Jugador) References Fixture.Jugador();

ForeignKey EquipoFK(Equipo) References Fixture.Equipo();

Method %OnBeforeSave(insert As %Boolean) As %Status [ Private, ServerOnly = 1 ]
{
    if ..Jugador.Equipo '= ..Equipo {
        quit $$$ERROR($$$GeneralError, "El equipo del evento no coincide con el del jugador "_..Jugador.Codigo)
    }
    quit $$$OK
}

/// Solo se agregan eventos a partidos EN_JUEGO, también por SQL.
/// Se lee el estado guardado del partido: es el que vale aunque haya cambios en memoria.
Trigger SoloEnJuego [ Event = INSERT, Foreach = row/object, Time = BEFORE ]
{
    new estado
    set estado = ##class(Fixture.Partido).EstadoGetStored({Partido})
    if estado '= "EN_JUEGO" {
        set %ok = 0, %msg = "No se pueden agregar eventos: el partido está "_estado
    }
}

/// Un evento registrado no se modifica (inalterable), ni por objetos ni por SQL.
Trigger Inalterable [ Event = UPDATE, Foreach = row/object, Time = BEFORE ]
{
    set %ok = 0, %msg = "Los eventos registrados son inalterables (evento "_{ID}_")"
}

}
