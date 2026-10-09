/// Estadio donde se juega un partido. Mismos códigos que en los hitos anteriores (S01...).
Class Fixture.Sede Extends %Persistent
{

Property Codigo As %String(MAXLEN = 3) [ Required ];

Property Estadio As %String(MAXLEN = 80) [ Required ];

Property Capacidad As %Integer(MINVAL = 1);

/// Componente embebido: se guarda junto con la sede.
Property Ubicacion As Fixture.Direccion [ Required ];

}
