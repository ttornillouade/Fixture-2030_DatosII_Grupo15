/// Árbitro habilitado para dirigir partidos del torneo (RF4: hereda de Persona).
Class Fixture.Arbitro Extends Fixture.Persona
{

Property Licencia As %String(MAXLEN = 20) [ Required ];

Property Categoria As %String(VALUELIST = ",FIFA,INTERNACIONAL,NACIONAL") [ Required ];

Index LicenciaIdx On Licencia [ Unique ];

/// Partido.Asistentes es una lista de referencias y a los elementos de una lista no se les
/// puede declarar ForeignKey. Este trigger cubre ese hueco: un árbitro que figura como
/// asistente en algún partido no se puede borrar (ni por objetos ni por SQL).
/// El árbitro principal ya está protegido por Partido.ArbitroPrincipalFK.
Trigger AsistenteEnPartido [ Event = DELETE, Foreach = row/object, Time = BEFORE ]
{
    new rs
    set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT TOP 1 Codigo FROM Fixture.Partido WHERE FOR SOME %ELEMENT(Asistentes) (%VALUE = ?)", {ID})
    if rs.%Next() {
        set %ok = 0, %msg = "El árbitro "_{Licencia}_" es asistente en "_rs.%Get("Codigo")_": no se puede borrar"
    }
}

}
