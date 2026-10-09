/// Árbitro del torneo (RF4: hereda de Persona).
Class Fixture.Arbitro Extends Fixture.Persona
{

Property Licencia As %String(MAXLEN = 20) [ Required ];

Property Rol As %String(VALUELIST = ",PRINCIPAL,ASISTENTE,CUARTO") [ Required ];

}
