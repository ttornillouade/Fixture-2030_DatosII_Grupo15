/// Datos comunes de las personas del Fixture (RF4).
/// Jugador y Arbitro heredan de esta clase: son tipos estables, no estados.
Class Fixture.Persona Extends %Persistent [ Abstract ]
{

Property Nombre As %String(MAXLEN = 60) [ Required ];

Property Apellido As %String(MAXLEN = 60) [ Required ];

/// Código ISO de 3 letras (URY, ARG, ESP...).
Property Nacionalidad As %String(MAXLEN = 3) [ Required ];

Property FechaNacimiento As %Date;

}
