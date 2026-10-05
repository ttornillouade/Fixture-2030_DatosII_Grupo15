/// Partido del Fixture 2030: una máquina de estados PROGRAMADO -> EN_JUEGO -> FINALIZADO.
/// Es el padre de sus eventos (relación parent/children, RF3): los eventos se guardan con
/// el partido en un solo %Save (RF6) y se borran con él.
///
/// Las reglas se aplican en tres niveles, todos dentro de la clase:
///   1. Métodos de negocio (Iniciar, RegistrarEvento, Finalizar): la forma normal de operar.
///   2. %OnBeforeSave: valida el objeto completo al guardarlo por objetos.
///   3. Triggers Foreach = row/object: valen también para INSERT/UPDATE/DELETE por SQL,
///      así que la proyección SQL (RF8) no es una puerta trasera para saltear la máquina de estados.
Class Fixture.Partido Extends %Persistent
{

Parameter MAXASISTENTES = 3;

Property Codigo As %String(MAXLEN = 4, PATTERN = "1""P""3N") [ Required ];

Property Fase As %String(VALUELIST = ",grupos,dieciseisavos,octavos,cuartos,semifinal,tercer_puesto,final") [ Required ];

Property FechaHora As %TimeStamp [ Required ];

Property Sede As Fixture.Sede [ Required ];

Property EquipoLocal As Fixture.Equipo [ Required ];

Property EquipoVisitante As Fixture.Equipo [ Required ];

Property ArbitroPrincipal As Fixture.Arbitro [ Required ];

/// Grupo delimitado de árbitros asistentes (máximo MAXASISTENTES).
Property Asistentes As list Of Fixture.Arbitro;

Property Estado As %String(VALUELIST = ",PROGRAMADO,EN_JUEGO,FINALIZADO") [ InitialExpression = "PROGRAMADO", Required ];

Relationship Eventos As Fixture.Evento [ Cardinality = children, Inverse = Partido ];

Index CodigoIdx On Codigo [ Unique ];

Index SedeIdx On Sede;

Index EquipoLocalIdx On EquipoLocal;

Index EquipoVisitanteIdx On EquipoVisitante;

/// Integridad referencial de las referencias simples: no se puede borrar una sede,
/// un equipo o un árbitro que figura en un partido.
ForeignKey SedeFK(Sede) References Fixture.Sede();

ForeignKey EquipoLocalFK(EquipoLocal) References Fixture.Equipo();

ForeignKey EquipoVisitanteFK(EquipoVisitante) References Fixture.Equipo();

ForeignKey ArbitroPrincipalFK(ArbitroPrincipal) References Fixture.Arbitro();

/// Única fuente de verdad de la máquina de estados (la usan métodos y triggers).
ClassMethod TransicionValida(desde As %String, hacia As %String) As %Boolean [ CodeMode = expression ]
{
((desde = "PROGRAMADO") && (hacia = "EN_JUEGO")) || ((desde = "EN_JUEGO") && (hacia = "FINALIZADO"))
}

/// PROGRAMADO -> EN_JUEGO. Valida que ambas alineaciones estén completas.
/// No guarda: permite armar el partido y sus eventos en memoria y persistir todo con un %Save.
Method Iniciar() As %Status
{
    if '..TransicionValida(..Estado, "EN_JUEGO") {
        quit $$$ERROR($$$GeneralError, "Transición ilegal en "_..Codigo_": "_..Estado_" -> EN_JUEGO")
    }
    set minimo = ##class(Fixture.Equipo).#MINALINEACION
    for equipo = ..EquipoLocal, ..EquipoVisitante {
        set n = equipo.Jugadores.Count()
        if n < minimo {
            return $$$ERROR($$$GeneralError, "Alineación incompleta: "_equipo.Codigo_" tiene "_n_" jugadores (mínimo "_minimo_")")
        }
    }
    set i%Estado = "EN_JUEGO"
    quit $$$OK
}

/// Agrega un evento al partido en memoria. Se persiste con el próximo %Save del partido.
/// Reglas: el partido debe estar EN_JUEGO, el jugador debe pertenecer a uno de los dos
/// equipos y un jugador expulsado no puede tener eventos posteriores.
Method RegistrarEvento(tipo As %String, minuto As %Integer, jugador As Fixture.Jugador, Output evento As Fixture.Evento) As %Status
{
    set evento = ""
    if ..Estado '= "EN_JUEGO" {
        quit $$$ERROR($$$GeneralError, "No se pueden registrar eventos en "_..Codigo_": el partido está "_..Estado)
    }
    if '$ISOBJECT(jugador) {
        quit $$$ERROR($$$GeneralError, "El evento necesita un jugador")
    }
    if (jugador.Equipo '= ..EquipoLocal) && (jugador.Equipo '= ..EquipoVisitante) {
        quit $$$ERROR($$$GeneralError, "El jugador "_jugador.Codigo_" no juega en "_..Codigo)
    }
    set expulsion = ..MinutoExpulsion(jugador)
    if (expulsion '= "") && (minuto >= expulsion) {
        quit $$$ERROR($$$GeneralError, "El jugador "_jugador.Codigo_" fue expulsado en el minuto "_expulsion)
    }
    // Se validan tipo y minuto antes de crear el hijo, para no dejar el partido con un
    // evento inválido en memoria. El objeto completo se valida igual al guardarlo.
    if (tipo = "") || (minuto = "") {
        quit $$$ERROR($$$GeneralError, "El tipo y el minuto del evento son obligatorios")
    }
    set sc = ##class(Fixture.Evento).TipoIsValid(tipo)
    quit:$$$ISERR(sc) sc
    set sc = ##class(Fixture.Evento).MinutoIsValid(minuto)
    quit:$$$ISERR(sc) sc
    set nuevo = ##class(Fixture.Evento).%New()
    set nuevo.Tipo = tipo
    set nuevo.Minuto = minuto
    set nuevo.Jugador = jugador
    set nuevo.Equipo = jugador.Equipo
    set nuevo.Partido = $this
    set evento = nuevo
    quit $$$OK
}

/// EN_JUEGO -> FINALIZADO. Cierra el acta: guarda los eventos pendientes y el cambio de
/// estado en una sola transacción. Después, el partido no admite más eventos.
Method Finalizar() As %Status
{
    if '..TransicionValida(..Estado, "FINALIZADO") {
        quit $$$ERROR($$$GeneralError, "Transición ilegal en "_..Codigo_": "_..Estado_" -> FINALIZADO")
    }
    tstart
    set sc = ..%Save()
    if $$$ISOK(sc) {
        set i%Estado = "FINALIZADO"
        set sc = ..%Save()
    }
    if $$$ISERR(sc) {
        trollback 1
        set i%Estado = "EN_JUEGO"
        quit sc
    }
    tcommit
    quit $$$OK
}

/// Minuto de la tarjeta roja del jugador en este partido, o "" si no fue expulsado.
Method MinutoExpulsion(jugador As Fixture.Jugador) As %String
{
    set minuto = "", clave = ""
    for {
        set ev = ..Eventos.GetNext(.clave)
        quit:clave=""
        if (ev.Tipo = "TARJETA_ROJA") && (ev.Jugador = jugador) && ((minuto = "") || (ev.Minuto < minuto)) {
            set minuto = ev.Minuto
        }
    }
    quit minuto
}

/// Resultado calculado navegando los eventos (sin SQL): "local-visitante".
Method Marcador() As %String
{
    set local = 0, visitante = 0, clave = ""
    for {
        set ev = ..Eventos.GetNext(.clave)
        quit:clave=""
        continue:ev.Tipo'="GOL"
        if ev.Equipo = ..EquipoLocal { set local = local + 1 } else { set visitante = visitante + 1 }
    }
    quit local_"-"_visitante
}

/// Validación del objeto completo al guardarlo por objetos.
Method %OnBeforeSave(insert As %Boolean) As %Status [ Private, ServerOnly = 1 ]
{
    if (..EquipoLocal '= "") && (..EquipoLocal = ..EquipoVisitante) {
        quit $$$ERROR($$$GeneralError, "Un equipo no puede jugar contra sí mismo ("_..EquipoLocal.Codigo_")")
    }
    if ..Asistentes.Count() > ..#MAXASISTENTES {
        quit $$$ERROR($$$GeneralError, "El partido admite como máximo "_..#MAXASISTENTES_" árbitros asistentes")
    }
    for i = 1:1:..Asistentes.Count() {
        if ..Asistentes.GetAt(i) = ..ArbitroPrincipal {
            return $$$ERROR($$$GeneralError, "El árbitro principal no puede ser también asistente")
        }
    }
    quit $$$OK
}

/// Máquina de estados también por SQL: un partido nace PROGRAMADO o EN_JUEGO y solo avanza
/// por transiciones válidas.
Trigger ReglasEstado [ Event = INSERT/UPDATE, Foreach = row/object, Time = BEFORE ]
{
    new desde, hacia
    set hacia = {Estado*N}
    if {%%OPERATION} = "INSERT" {
        if (hacia '= "PROGRAMADO") && (hacia '= "EN_JUEGO") {
            set %ok = 0, %msg = "Un partido nuevo debe estar PROGRAMADO o EN_JUEGO, no "_hacia
        }
    } else {
        set desde = {Estado*O}
        if (desde '= hacia) && '##class(Fixture.Partido).TransicionValida(desde, hacia) {
            set %ok = 0, %msg = "Transición ilegal de estado: "_desde_" -> "_hacia
        }
    }
    if %ok && ({EquipoLocal*N} = {EquipoVisitante*N}) {
        set %ok = 0, %msg = "Un equipo no puede jugar contra sí mismo"
    }
}

/// Un partido FINALIZADO es un acta oficial: no se borra. Uno PROGRAMADO o EN_JUEGO sí,
/// y sus eventos se borran en cascada (parent/children).
Trigger ActaOficial [ Event = DELETE, Foreach = row/object, Time = BEFORE ]
{
    if {Estado} = "FINALIZADO" {
        set %ok = 0, %msg = "El partido "_{Codigo}_" está FINALIZADO: el acta oficial no se puede borrar"
    }
}

}
