/// Director técnico de una selección (RF4: hereda de Persona).
Class Fixture.Tecnico Extends Fixture.Persona
{

/// Licencia de entrenador (PRO es la exigida para torneos de selecciones).
Property Licencia As %String(VALUELIST = ",PRO,A,B") [ Required ];

}
