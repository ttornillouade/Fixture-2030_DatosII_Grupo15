/// Datos comunes de las personas del Fixture (RF4: clase base de la herencia).
Class Fixture.Persona Extends %Persistent [ Abstract ]
{

Property Nombre As %String [ Required ];

Property Apellido As %String [ Required ];

Property Nacionalidad As %String [ Required ];

}
