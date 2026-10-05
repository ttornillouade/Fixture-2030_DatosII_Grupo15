/// Persona del dominio del Fixture 2030 (RF4).
/// Clase base: Jugador, Arbitro y Tecnico heredan de ella y comparten su extent,
/// así que en SQL existe una sola tabla Fixture.Persona con todas las personas y
/// una tabla por subclase con sus columnas propias.
/// La herencia modela tipos que no cambian (un árbitro no se convierte en jugador);
/// los estados que sí cambian (lesionado, expulsado) son datos, no subclases.
Class Fixture.Persona Extends %Persistent [ Abstract ]
{

/// Documento de identidad. Único entre todas las personas del dominio.
Property Documento As %String(MAXLEN = 20) [ Required ];

Property Nombre As %String(MAXLEN = 60) [ Required ];

Property Apellido As %String(MAXLEN = 60) [ Required ];

Property FechaNacimiento As %Date [ Required ];

/// Código ISO 3166-1 alfa-3 (URY, ARG, ESP...).
Property Nacionalidad As %String(MAXLEN = 3, PATTERN = "3U") [ Required ];

Index DocumentoIdx On Documento [ Unique ];

Method NombreCompleto() As %String [ CodeMode = expression ]
{
..Nombre_" "_..Apellido
}

/// Edad en años cumplidos a la fecha indicada (por defecto, hoy).
Method Edad(fecha As %Date = {+$HOROLOG}) As %Integer [ CodeMode = expression ]
{
($ZDATE(fecha, 8) - $ZDATE(..FechaNacimiento, 8)) \ 10000
}

}
