/// Árbitro habilitado para dirigir partidos del torneo (RF4: hereda de Persona).
Class Fixture.Arbitro Extends Fixture.Persona
{

Property Licencia As %String(MAXLEN = 20) [ Required ];

Property Categoria As %String(VALUELIST = ",FIFA,INTERNACIONAL,NACIONAL") [ Required ];

Index LicenciaIdx On Licencia [ Unique ];

}
