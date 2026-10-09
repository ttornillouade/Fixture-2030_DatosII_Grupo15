/// Dirección de una sede. Composición: no tiene identidad propia y se guarda dentro
/// del objeto que la contiene (%SerialObject).
Class Fixture.Direccion Extends %SerialObject
{

Property Calle As %String(MAXLEN = 80);

Property Ciudad As %String(MAXLEN = 60) [ Required ];

/// Código ISO de 3 letras.
Property Pais As %String(MAXLEN = 3) [ Required ];

}
