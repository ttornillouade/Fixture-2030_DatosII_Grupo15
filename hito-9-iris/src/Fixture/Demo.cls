/// Demostración del Hito 9, invocable desde la terminal de IRIS:
///   do ##class(Fixture.Demo).Ejecutar()
/// Cada sección también se puede correr por separado (ver README).
/// Los datos son los del TPO: P001 = E001 vs E002 en S01 (Estadio Centenario), fase de grupos.
Class Fixture.Demo [ Abstract ]
{

ClassMethod Ejecutar()
{
    do ..SalidaUtf8()
    do ..Limpiar()
    do ..CargarArbol()
    do ..Navegar()
    do ..FallasControladas()
    do ..ReglasDeEstado()
    do ..ProyeccionSQL()
    do ..Integridad()
    do ..Titulo("Resumen final")
    do ..MostrarConteos()
    write !,"Pruebas con resultado esperado: ",+$GET(^||demo("ok"))," | inesperado: ",+$GET(^||demo("mal")),!
}

/// Borra los datos de la demo (no las clases). Hace que Ejecutar() sea repetible.
ClassMethod Limpiar()
{
    do ..SalidaUtf8()
    kill ^||demo
    do ##class(Fixture.Evento).%KillExtent()
    do ##class(Fixture.Partido).%KillExtent()
    do ##class(Fixture.Equipo).%KillExtent()
    do ##class(Fixture.Persona).%KillExtent()
    do ##class(Fixture.Sede).%KillExtent()
}

// ---------------------------------------------------------------------------------------
// RF6 — Árbol de objetos guardado con una sola invocación de %Save
// ---------------------------------------------------------------------------------------

ClassMethod CargarArbol()
{
    do ..SalidaUtf8()
    do ..Titulo("RF6 - Carga atómica de un árbol de objetos con un solo %Save")
    write "Antes de la carga:",!
    do ..MostrarConteos()

    set sede = ..NuevaSede("S01", "Estadio Centenario", "Montevideo", "URY", 60235)
    set local = ..NuevoEquipo("E001", "Seleccion 001", "Pais 001", "CONMEBOL", "A", "URY", 14, .jugadores)
    set visitante = ..NuevoEquipo("E002", "Seleccion 002", "Pais 002", "UEFA", "A", "ESP", 14, .jugadores)

    set p = ##class(Fixture.Partido).%New()
    set p.Codigo = "P001", p.Fase = "grupos", p.FechaHora = "2030-06-08 16:00:00"
    set p.Sede = sede, p.EquipoLocal = local, p.EquipoVisitante = visitante
    set p.ArbitroPrincipal = ..NuevoArbitro("A01", "FIFA", "ARG")
    do p.Asistentes.Insert(..NuevoArbitro("A02", "FIFA", "BRA"))
    do p.Asistentes.Insert(..NuevoArbitro("A03", "FIFA", "CHL"))

    do ..Esperar("Iniciar P001 (alineaciones de 14 y 14 jugadores)", p.Iniciar(), 1)
    do ..Esperar("Gol de E001-J09 (23')", p.RegistrarEvento("GOL", 23, jugadores("E001-J09")), 1)
    do ..Esperar("Amarilla a E002-J04 (31')", p.RegistrarEvento("TARJETA_AMARILLA", 31, jugadores("E002-J04")), 1)
    do ..Esperar("Gol de E002-J10 (58')", p.RegistrarEvento("GOL", 58, jugadores("E002-J10")), 1)
    do ..Esperar("Sustitución de E001-J11 (60')", p.RegistrarEvento("SUSTITUCION", 60, jugadores("E001-J11")), 1)
    do ..Esperar("Roja a E002-J05 (71')", p.RegistrarEvento("TARJETA_ROJA", 71, jugadores("E002-J05")), 1)
    do ..Esperar("Gol de E001-J10 (77')", p.RegistrarEvento("GOL", 77, jugadores("E001-J10")), 1)

    write !,"En memoria, sin guardar: partido id='",p.%Id(),"', equipo local id='",local.%Id()
    write "', eventos en el partido=",p.Eventos.Count(),!
    write !,">>> set sc = p.%Save()   (única invocación de guardado)",!
    set sc = p.%Save()
    do ..Esperar("Guardar el árbol completo desde el partido", sc, 1)

    write !,"Ids asignados: partido=",p.%Id(),", sede=",sede.%Id(),", local=",local.%Id()
    set clave = "", primero = p.Eventos.GetNext(.clave)
    write ", visitante=",visitante.%Id(),", primer evento=",$SELECT($ISOBJECT(primero): primero.%Id(), 1: "-"),!
    write !,"Después de la carga:",!
    do ..MostrarConteos()
}

// ---------------------------------------------------------------------------------------
// RF7 — Navegación por referencias de objetos (sin SQL)
// ---------------------------------------------------------------------------------------

ClassMethod Navegar()
{
    do ..SalidaUtf8()
    do ..Titulo("RF7 - Navegación por referencias (sin SQL)")
    // Se abre desde disco por índice único: nada queda de la carga anterior en memoria.
    set p = ##class(Fixture.Partido).CodigoIdxOpen("P001")
    write "Partido ",p.Codigo," | fase ",p.Fase," | ",p.FechaHora," | estado ",p.Estado,!
    write "  Sede: ",p.Sede.Estadio," (",p.Sede.Ciudad,", ",p.Sede.Pais,"), capacidad ",p.Sede.Capacidad,!
    for rol = "EquipoLocal", "EquipoVisitante" {
        set e = $PROPERTY(p, rol)
        write "  ",rol,": ",e.Codigo," ",e.Nombre," (",e.Confederacion,", grupo ",e.Grupo,")"
        write " | DT ",e.Tecnico.NombreCompleto()," | plantel ",e.Jugadores.Count()," jugadores",!
    }
    write "  Árbitro principal: ",p.ArbitroPrincipal.NombreCompleto()," (",p.ArbitroPrincipal.Categoria,")",!
    for i = 1:1:p.Asistentes.Count() {
        write "  Asistente ",i,": ",p.Asistentes.GetAt(i).NombreCompleto(),!
    }
    write "  Eventos (partido -> hijos), ordenados por minuto:",!
    set clave = ""
    for {
        set ev = p.Eventos.GetNext(.clave)
        quit:clave=""
        set orden(ev.Minuto, clave) = ev
    }
    set minuto = ""
    for {
        set minuto = $ORDER(orden(minuto))
        quit:minuto=""
        set clave = ""
        for {
            set clave = $ORDER(orden(minuto, clave), 1, ev)
            quit:clave=""
            write "    ",$JUSTIFY(ev.Minuto, 3),"' ",$JUSTIFY(ev.Tipo, -18)," ",ev.Jugador.Codigo," ",ev.Jugador.NombreCompleto()
            write " (",ev.Equipo.Codigo,") id=",ev.%Id(),!
        }
    }
    write "  Marcador calculado navegando los eventos: ",p.Marcador(),!

    write !,"Navegación inversa (bidireccional):",!
    set clave = "", ev = p.Eventos.GetNext(.clave)
    write "  evento ",ev.%Id()," -> Partido -> Sede: ",ev.Partido.Codigo," en ",ev.Partido.Sede.Estadio,!
    set j = ##class(Fixture.Jugador).CodigoIdxOpen("E001-J09")
    write "  jugador ",j.Codigo," -> Equipo: ",j.Equipo.Nombre," -> Jugadores: ",j.Equipo.Jugadores.Count()
    write " -> Tecnico: ",j.Equipo.Tecnico.NombreCompleto(),!
    write "  ",j.NombreCompleto(),": dorsal ",j.Dorsal,", ",j.PosicionLogicalToDisplay(j.Posicion),", ",j.Edad()," años",!

    write !,"Herencia y polimorfismo: abrir por la clase base Persona devuelve la subclase real",!
    for id = j.%Id(), p.ArbitroPrincipal.%Id(), p.EquipoLocal.Tecnico.%Id() {
        set persona = ##class(Fixture.Persona).%OpenId(id)
        write "  Persona.%OpenId(",id,") -> ",$CLASSNAME(persona)," | ",persona.NombreCompleto(),!
    }
}

// ---------------------------------------------------------------------------------------
// RF5 — Fallas de carga controladas (propiedades obligatorias y tipos estrictos)
// ---------------------------------------------------------------------------------------

ClassMethod FallasControladas()
{
    do ..SalidaUtf8()
    do ..Titulo("RF5 - Fallas de carga controladas")
    set antes = ..Contar("Fixture.Jugador")
    do ..Esperar("Jugador sin Documento (propiedad [Required])", ..JugadorSinDocumento(), 0)
    do ..Esperar("Nacionalidad 'ury' en minúsculas (PATTERN 3U)", ..JugadorConDato("Nacionalidad", "ury"), 0)
    do ..Esperar("Dorsal 120 (MAXVAL 99)", ..JugadorConDato("Dorsal", 120), 0)
    do ..Esperar("Posición 'LIBERO' (VALUELIST)", ..JugadorConDato("Posicion", "LIBERO"), 0)
    do ..Esperar("Dorsal 9 repetido en E001 (índice único Equipo+Dorsal)", ..JugadorConDato("Dorsal", 9), 0)
    write "  Jugadores antes: ",antes," | después: ",..Contar("Fixture.Jugador"),!

    write !,"Atomicidad: equipo E003 con 11 jugadores, uno sin FechaNacimiento -> no se guarda nada",!
    set antes = ..Contar("Fixture.Persona")_"/"_..Contar("Fixture.Equipo")
    do ..Esperar("Guardar E003 con un jugador inválido", ..EquipoConJugadorInvalido(), 0)
    write "  Personas/Equipos antes: ",antes," | después: ",..Contar("Fixture.Persona"),"/",..Contar("Fixture.Equipo"),!
}

ClassMethod JugadorSinDocumento() As %Status
{
    set j = ..NuevoJugador(##class(Fixture.Equipo).CodigoIdxOpen("E001"), 15, "URY")
    set j.Documento = ""
    quit j.%Save()
}

ClassMethod JugadorConDato(propiedad As %String, valor As %String) As %Status
{
    set j = ..NuevoJugador(##class(Fixture.Equipo).CodigoIdxOpen("E001"), 15, "URY")
    set $PROPERTY(j, propiedad) = valor
    quit j.%Save()
}

ClassMethod EquipoConJugadorInvalido() As %Status
{
    set e = ..NuevoEquipo("E003", "Seleccion 003", "Pais 003", "CAF", "A", "MAR", 11, .jugadores)
    set jugadores("E003-J07").FechaNacimiento = ""
    quit e.%Save()
}

// ---------------------------------------------------------------------------------------
// RF9 — Máquina de estados del partido y eventos inalterables
// ---------------------------------------------------------------------------------------

ClassMethod ReglasDeEstado()
{
    do ..SalidaUtf8()
    do ..Titulo("RF9 - Transiciones de estado ilegales")
    set p = ##class(Fixture.Partido).CodigoIdxOpen("P001")
    set j = ##class(Fixture.Jugador).CodigoIdxOpen("E001-J09")
    set eventos = p.Eventos.Count()

    do ..Esperar("Finalizar P001 (EN_JUEGO -> FINALIZADO, guarda el acta)", p.Finalizar(), 1)
    write "  Estado guardado: ",##class(Fixture.Partido).EstadoGetStored(p.%Id()),!
    do ..Esperar("Iniciar P001 de nuevo (FINALIZADO -> EN_JUEGO)", p.Iniciar(), 0)
    do ..Esperar("Gol en el minuto 0 en P001 FINALIZADO (ejemplo de la consigna)", p.RegistrarEvento("GOL", 0, j), 0)
    do ..Esperar("Gol en el minuto 88 en P001 FINALIZADO", p.RegistrarEvento("GOL", 88, j), 0)
    write !,"Atomicidad: un mismo %Save lleva un cambio válido (capacidad de la sede) y un evento ilegal",!
    write "-> se rechaza el guardado completo y no queda ninguno de los dos cambios",!
    do ..Esperar("Saltear el método: Eventos.Insert + %Save en P001 FINALIZADO", ..EventoPorFuera(p, j), 0)
    write "  Eventos de P001 antes: ",eventos," | después: ",..Contar("Fixture.Evento", "Partido->Codigo = 'P001'"),!
    write "  Capacidad de S01 en memoria: ",p.Sede.Capacidad," | en disco: ",##class(Fixture.Sede).CapacidadGetStored(p.Sede.%Id())," (revertida)",!

    write !,"Las mismas reglas valen por SQL (triggers Foreach = row/object):",!
    do ..EsperarSql("INSERT de un evento en P001 FINALIZADO",
        "INSERT INTO Fixture.Evento (Partido, Tipo, Minuto, Jugador, Equipo, RegistradoEn) VALUES (?, 'GOL', 89, ?, ?, CURRENT_TIMESTAMP)",
        0, p.%Id(), j.%Id(), j.Equipo.%Id())
    do ..EsperarSql("UPDATE del minuto de un evento registrado",
        "UPDATE Fixture.Evento SET Minuto = 1 WHERE Partido->Codigo = 'P001' AND Tipo = 'GOL'", 0)
    do ..EsperarSql("UPDATE de P001: FINALIZADO -> EN_JUEGO",
        "UPDATE Fixture.Partido SET Estado = 'EN_JUEGO' WHERE Codigo = 'P001'", 0)

    write !,"Segundo árbol: E003 (11 jugadores), E004 (5 jugadores) y P002 = E003 vs E004 PROGRAMADO",!
    set e3 = ..NuevoEquipo("E003", "Seleccion 003", "Pais 003", "CAF", "A", "MAR", 11, .jugadores)
    set e4 = ..NuevoEquipo("E004", "Seleccion 004", "Pais 004", "AFC", "A", "JPN", 5, .jugadores)
    set p2 = ..NuevoPartido("P002", "S01", e3, e4, "A04")
    do ..Esperar("Guardar P002 (con E003, E004 y sus jugadores)", p2.%Save(), 1)
    do ..Esperar("Finalizar P002 PROGRAMADO (saltea EN_JUEGO)", p2.Finalizar(), 0)
    do ..Esperar("Iniciar P002 con E004 de 5 jugadores (alineación incompleta)", p2.Iniciar(), 0)
    do ..Esperar("Partido E003 vs E003", ..NuevoPartido("P009", "S01", e3, e3, "A05").%Save(), 0)
    set p3 = ..NuevoPartido("P003", "S01", ##class(Fixture.Equipo).CodigoIdxOpen("E001"), e3, "A06")
    do p3.Asistentes.Insert(p3.ArbitroPrincipal)
    do ..Esperar("Árbitro principal repetido como asistente", p3.%Save(), 0)
    do p3.Asistentes.Clear()
    do ..Esperar("Iniciar P003 = E001 vs E003", p3.Iniciar(), 1)
    do ..Esperar("Evento de E004-J01, que no juega P003", p3.RegistrarEvento("GOL", 10, jugadores("E004-J01")), 0)
    do ..Esperar("Roja a E003-J05 (30')", p3.RegistrarEvento("TARJETA_ROJA", 30, jugadores("E003-J05")), 1)
    do ..Esperar("Gol de E003-J05 (40'), ya expulsado", p3.RegistrarEvento("GOL", 40, jugadores("E003-J05")), 0)
    do ..Esperar("Guardar P003 EN_JUEGO con 1 evento", p3.%Save(), 1)
}

ClassMethod EventoPorFuera(p As Fixture.Partido, j As Fixture.Jugador) As %Status
{
    set ev = ##class(Fixture.Evento).%New()
    set ev.Tipo = "GOL", ev.Minuto = 90, ev.Jugador = j, ev.Equipo = j.Equipo
    set p.Sede.Capacidad = 1000
    do p.Eventos.Insert(ev)
    quit p.%Save()
}

// ---------------------------------------------------------------------------------------
// RF8 — Proyección multimodelo: los mismos datos por SQL
// ---------------------------------------------------------------------------------------

ClassMethod ProyeccionSQL()
{
    do ..SalidaUtf8()
    do ..Titulo("RF8 - Proyección SQL de los objetos")
    set p = ##class(Fixture.Partido).CodigoIdxOpen("P001")
    write "Eventos de P001 por objetos (p.Eventos.Count()): ",p.Eventos.Count()
    write " | por SQL (COUNT(*)): ",..Contar("Fixture.Evento", "Partido->Codigo = 'P001'"),!

    do ..Consulta("SELECT p.Codigo, p.Estado, p.Sede->Estadio AS Sede, p.EquipoLocal->Codigo AS EqLocal, p.EquipoVisitante->Codigo AS EqVisitante, p.ArbitroPrincipal->Apellido AS Arbitro FROM Fixture.Partido p ORDER BY p.Codigo")
    do ..Consulta("SELECT e.ID, e.Minuto, e.Tipo, e.Jugador->Codigo AS Jugador, e.Equipo->Nombre AS Equipo FROM Fixture.Evento e WHERE e.Partido->Codigo = 'P001' ORDER BY e.Minuto")
    do ..Consulta("SELECT x__classname AS Clase, COUNT(*) AS Personas FROM Fixture.Persona GROUP BY x__classname")
    do ..Consulta("SELECT TOP 5 j.Codigo, j.Apellido, j.Dorsal, %EXTERNAL(j.Posicion) AS Posicion, j.Equipo->Codigo AS Equipo FROM Fixture.Jugador j WHERE j.Equipo->Codigo = 'E001' ORDER BY j.Dorsal")

    write !,"RNF3 - Plan de ejecución: el lado ""muchos"" se lee por su índice, no recorriendo la tabla",!
    do ..Plan("SELECT Codigo FROM Fixture.Jugador WHERE Equipo = 1")
    do ..Plan("SELECT Minuto FROM Fixture.Evento WHERE Jugador = 14")

    write !,"SQL también escribe objetos (multimodelo en los dos sentidos):",!
    do ..EsperarSql("INSERT de la sede S02 por SQL",
        "INSERT INTO Fixture.Sede (Codigo, Estadio, Ciudad, Pais, Capacidad) VALUES ('S02', 'Estadio Monumental', 'Buenos Aires', 'ARG', 84567)", 1)
    set s2 = ##class(Fixture.Sede).CodigoIdxOpen("S02")
    write "  Abierta como objeto: ",$CLASSNAME(s2)," ",s2.Codigo," ",s2.Estadio," (",s2.Ciudad,")",!
    do ..EsperarSql("UPDATE del nombre de E001 por SQL",
        "UPDATE Fixture.Equipo SET Nombre = 'Seleccion 001 (Uruguay)' WHERE Codigo = 'E001'", 1)
    write "  Leído por objetos: ",##class(Fixture.Equipo).CodigoIdxOpen("E001").Nombre,!
    do ..EsperarSql("INSERT de una sede con Pais 'Uruguay' (mismo PATTERN que por objetos)",
        "INSERT INTO Fixture.Sede (Codigo, Estadio, Ciudad, Pais, Capacidad) VALUES ('S03', 'Estadio X', 'Asuncion', 'Uruguay', 45000)", 0)
}

// ---------------------------------------------------------------------------------------
// Matriz de integridad — borrados
// ---------------------------------------------------------------------------------------

ClassMethod Integridad()
{
    do ..SalidaUtf8()
    do ..Titulo("Integridad referencial al borrar")
    set eventos = ..Contar("Fixture.Evento")
    do ..Esperar("Borrar P001 FINALIZADO (acta oficial)", ##class(Fixture.Partido).CodigoIdxDelete("P001"), 0)
    do ..Esperar("Borrar P003 EN_JUEGO: sus eventos se borran en cascada", ##class(Fixture.Partido).CodigoIdxDelete("P003"), 1)
    write "  Eventos antes: ",eventos," | después: ",..Contar("Fixture.Evento")," (P001 conserva los suyos)",!
    do ..Esperar("Borrar E004, que tiene jugadores y figura en P002", ##class(Fixture.Equipo).CodigoIdxDelete("E004"), 0)
    do ..Esperar("Borrar P002 PROGRAMADO, sin eventos", ##class(Fixture.Partido).CodigoIdxDelete("P002"), 1)
    do ..Esperar("Borrar E004 ya sin partidos, pero con jugadores (OnDelete = noaction)", ##class(Fixture.Equipo).CodigoIdxDelete("E004"), 0)
    do ..Esperar("Borrar la sede S01, usada por P001", ##class(Fixture.Sede).CodigoIdxDelete("S01"), 0)
    do ..Esperar("Borrar el árbitro principal de P001", ##class(Fixture.Arbitro).LicenciaIdxDelete("LIC-A01"), 0)
    do ..Esperar("Borrar un árbitro asistente de P001 (trigger, la lista no admite ForeignKey)", ##class(Fixture.Arbitro).LicenciaIdxDelete("LIC-A03"), 0)
    do ..Esperar("Borrar el técnico de E001", ##class(Fixture.Persona).DocumentoIdxDelete("DOC-E001-DT"), 0)
    do ..Esperar("Borrar un jugador con eventos registrados (E001-J09)", ##class(Fixture.Jugador).CodigoIdxDelete("E001-J09"), 0)
}

// ---------------------------------------------------------------------------------------
// Constructores de datos
// ---------------------------------------------------------------------------------------

ClassMethod NuevaSede(codigo, estadio, ciudad, pais, capacidad) As Fixture.Sede
{
    set s = ##class(Fixture.Sede).%New()
    set s.Codigo = codigo, s.Estadio = estadio, s.Ciudad = ciudad, s.Pais = pais, s.Capacidad = capacidad
    quit s
}

/// Crea el equipo con su técnico y "cantidad" jugadores J01..Jnn. No guarda.
/// Devuelve los jugadores en jugadores("E001-J09") para usarlos en los eventos.
ClassMethod NuevoEquipo(codigo, nombre, pais, confederacion, grupo, nacionalidad, cantidad, ByRef jugadores) As Fixture.Equipo
{
    set e = ##class(Fixture.Equipo).%New()
    set e.Codigo = codigo, e.Nombre = nombre, e.Pais = pais, e.Confederacion = confederacion, e.Grupo = grupo
    set t = ##class(Fixture.Tecnico).%New()
    set t.Documento = "DOC-"_codigo_"-DT", t.Nombre = "Tecnico", t.Apellido = nombre
    set t.FechaNacimiento = $ZDATEH("1970-05-20", 3), t.Nacionalidad = nacionalidad, t.Licencia = "PRO"
    set e.Tecnico = t
    for n = 1:1:cantidad {
        set j = ..NuevoJugador(e, n, nacionalidad)
        set jugadores(j.Codigo) = j
    }
    quit e
}

ClassMethod NuevoJugador(equipo As Fixture.Equipo, n As %Integer, nacionalidad As %String) As Fixture.Jugador
{
    set nn = $TRANSLATE($JUSTIFY(n, 2), " ", "0")
    set j = ##class(Fixture.Jugador).%New()
    set j.Codigo = equipo.Codigo_"-J"_nn
    set j.Documento = "DOC-"_j.Codigo
    set j.Nombre = "Jugador "_nn, j.Apellido = equipo.Nombre
    set j.FechaNacimiento = $ZDATEH("1994-01-15", 3) + (n * 211)
    set j.Nacionalidad = nacionalidad
    set j.Dorsal = n
    set j.Posicion = $CASE(n, 1:"ARQ", 12:"ARQ", 2:"DEF", 3:"DEF", 4:"DEF", 5:"DEF", 13:"DEF", 10:"DEL", 11:"DEL", 14:"DEL", :"MED")
    set j.Equipo = equipo
    quit j
}

ClassMethod NuevoArbitro(codigo, categoria, nacionalidad) As Fixture.Arbitro
{
    set a = ##class(Fixture.Arbitro).%New()
    set a.Documento = "DOC-"_codigo, a.Nombre = "Arbitro", a.Apellido = codigo
    set a.FechaNacimiento = $ZDATEH("1985-09-10", 3), a.Nacionalidad = nacionalidad
    set a.Licencia = "LIC-"_codigo, a.Categoria = categoria
    quit a
}

ClassMethod NuevoPartido(codigo, sede, local, visitante, arbitro) As Fixture.Partido
{
    set p = ##class(Fixture.Partido).%New()
    set p.Codigo = codigo, p.Fase = "grupos", p.FechaHora = "2030-06-12 19:00:00"
    set p.Sede = ##class(Fixture.Sede).CodigoIdxOpen(sede)
    set p.EquipoLocal = local, p.EquipoVisitante = visitante
    set p.ArbitroPrincipal = ..NuevoArbitro(arbitro, "INTERNACIONAL", "PRT")
    quit p
}

// ---------------------------------------------------------------------------------------
// Salida
// ---------------------------------------------------------------------------------------

/// La terminal usada por docker exec no escribe en UTF-8 por defecto (se verían mal los acentos).
ClassMethod SalidaUtf8() [ CodeMode = expression ]
{
##class(%SYS.NLS.Device).SetIO("UTF8")
}

ClassMethod Titulo(texto As %String)
{
    write !,"========== ",texto," ==========",!
}

/// Informa el resultado y si coincide con lo esperado (1 = debe funcionar, 0 = debe rechazarse).
ClassMethod Esperar(descripcion As %String, sc As %Status, debeFuncionar As %Boolean)
{
    set funciono = $$$ISOK(sc)
    set marca = $SELECT(funciono = debeFuncionar: "[esperado]  ", 1: "[INESPERADO]")
    set ^||demo($SELECT(funciono = debeFuncionar: "ok", 1: "mal")) = $GET(^||demo($SELECT(funciono = debeFuncionar: "ok", 1: "mal"))) + 1
    write "  ",marca," ",$SELECT(funciono: "OK        ", 1: "RECHAZADO "),descripcion,!
    if 'funciono {
        write "               -> ",$PIECE($SYSTEM.Status.GetErrorText(sc), $CHAR(13,10)),!
    }
}

ClassMethod EsperarSql(descripcion As %String, sql As %String, debeFuncionar As %Boolean, args...)
{
    set rs = ##class(%SQL.Statement).%ExecDirect(, sql, args...)
    if rs.%SQLCODE < 0 {
        set sc = $$$ERROR($$$GeneralError, "SQLCODE "_rs.%SQLCODE_": "_rs.%Message)
    } else {
        set sc = $$$OK
    }
    do ..Esperar(descripcion_" ("_+rs.%ROWCOUNT_" filas)", sc, debeFuncionar)
}

ClassMethod Consulta(sql As %String)
{
    write !,"SQL> ",sql,!
    set rs = ##class(%SQL.Statement).%ExecDirect(, sql)
    if rs.%SQLCODE < 0 { write "  ERROR SQLCODE ",rs.%SQLCODE,": ",rs.%Message,! quit }
    do rs.%Display()
    write !
}

/// Muestra las líneas del plan (EXPLAIN) que indican qué mapa lee la consulta.
ClassMethod Plan(sql As %String)
{
    write "  SQL> ",sql,!
    set rs = ##class(%SQL.Statement).%ExecDirect(, "EXPLAIN "_sql)
    if (rs.%SQLCODE < 0) || 'rs.%Next() { write "    (plan no disponible: ",rs.%Message,")",! quit }
    set plan = rs.%GetData(1)
    for i = 1:1:$LENGTH(plan, $CHAR(10)) {
        set linea = $ZSTRIP($PIECE(plan, $CHAR(10), i), "<>W")
        write:((linea [ " map ") || (linea [ "Cost:")) "    ",linea,!
    }
}

ClassMethod Contar(tabla As %String, condicion As %String = "") As %Integer
{
    set sql = "SELECT COUNT(*) FROM "_tabla_$SELECT(condicion '= "": " WHERE "_condicion, 1: "")
    set rs = ##class(%SQL.Statement).%ExecDirect(, sql)
    quit $SELECT(rs.%Next(): rs.%GetData(1), 1: "?")
}

ClassMethod MostrarConteos()
{
    write "  Sedes=",..Contar("Fixture.Sede"),"  Equipos=",..Contar("Fixture.Equipo")
    write "  Personas=",..Contar("Fixture.Persona")," (Jugadores=",..Contar("Fixture.Jugador")
    write ", Tecnicos=",..Contar("Fixture.Tecnico"),", Arbitros=",..Contar("Fixture.Arbitro"),")"
    write "  Partidos=",..Contar("Fixture.Partido"),"  Eventos=",..Contar("Fixture.Evento"),!
}

}
