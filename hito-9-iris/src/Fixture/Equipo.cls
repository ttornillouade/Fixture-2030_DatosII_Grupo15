/// Selección participante. Mismos códigos y datos que la fuente de verdad del Hito 7 (E001...).
/// Lado "uno" de la relación Equipo -> Jugadores (RF3).
Class Fixture.Equipo Extends %Persistent
{

/// Plantel máximo por selección.
Parameter MAXJUGADORES = 26;

/// Jugadores necesarios para iniciar un partido.
Parameter MINALINEACION = 11;

Property Codigo As %String(MAXLEN = 4, PATTERN = "1""E""3N") [ Required ];

Property Nombre As %String(MAXLEN = 60) [ Required ];

Property Pais As %String(MAXLEN = 60) [ Required ];

Property Confederacion As %String(VALUELIST = ",AFC,CAF,CONCACAF,CONMEBOL,OFC,UEFA") [ Required ];

Property Grupo As %String(MAXLEN = 1, PATTERN = "1U");

/// Referencia simple: un técnico dirige a un solo equipo (índice único).
Property Tecnico As Fixture.Tecnico [ Required ];

Relationship Jugadores As Fixture.Jugador [ Cardinality = many, Inverse = Equipo ];

Index CodigoIdx On Codigo [ Unique ];

Index TecnicoIdx On Tecnico [ Unique ];

ForeignKey TecnicoFK(Tecnico) References Fixture.Tecnico();

/// Valida el objeto completo antes de guardarlo (además de [Required] y los tipos).
Method %OnBeforeSave(insert As %Boolean) As %Status [ Private, ServerOnly = 1 ]
{
    if ..Jugadores.Count() > ..#MAXJUGADORES {
        quit $$$ERROR($$$GeneralError, "El plantel de "_..Codigo_" supera los "_..#MAXJUGADORES_" jugadores")
    }
    quit $$$OK
}

}
