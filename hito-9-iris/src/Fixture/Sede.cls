/// Estadio donde se juega un partido. Mismos códigos que en los hitos anteriores (S01...).
Class Fixture.Sede Extends %Persistent
{

Property Codigo As %String(MAXLEN = 3, PATTERN = "1""S""2N") [ Required ];

Property Estadio As %String(MAXLEN = 80) [ Required ];

Property Ciudad As %String(MAXLEN = 60) [ Required ];

/// Código ISO 3166-1 alfa-3 del país sede.
Property Pais As %String(MAXLEN = 3, PATTERN = "3U") [ Required ];

Property Capacidad As %Integer(MAXVAL = 150000, MINVAL = 1000) [ Required ];

Index CodigoIdx On Codigo [ Unique ];

}
