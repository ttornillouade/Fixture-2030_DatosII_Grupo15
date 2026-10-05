# Diagrama de objetos

Clases del paquete `Fixture` (archivos en [`src/Fixture/`](../src/Fixture/)). Todas extienden
`%Persistent` y cada una se proyecta como tabla SQL del esquema `Fixture`.

Convenciones: `*` = propiedad obligatoria (`[Required]`); `«único»` = índice único;
`«idx»` = índice simple. Las relaciones con `<-->` son bidireccionales (`Relationship` con `Inverse`).

```mermaid
classDiagram
    direction LR

    class Persona {
        <<abstract>>
        +Documento* : %String «único»
        +Nombre* : %String
        +Apellido* : %String
        +FechaNacimiento* : %Date
        +Nacionalidad* : %String PATTERN 3U
        +NombreCompleto() %String
        +Edad(fecha) %Integer
    }
    class Jugador {
        +Codigo* : %String E001J09 «único»
        +Dorsal* : %Integer 1..99
        +Posicion* : ARQ/DEF/MED/DEL
        +Equipo* : Equipo «idx» (Relationship one)
    }
    class Arbitro {
        +Licencia* : %String «único»
        +Categoria* : FIFA/INTERNACIONAL/NACIONAL
        trigger AsistenteEnPartido()
    }
    class Tecnico {
        +Licencia* : PRO/A/B
    }
    class Equipo {
        +Codigo* : %String E001 «único»
        +Nombre* : %String
        +Pais* : %String
        +Confederacion* : AFC/CAF/CONCACAF/CONMEBOL/OFC/UEFA
        +Grupo : %String
        +Tecnico* : Tecnico «único»
        +Jugadores : Relationship many
        #%OnBeforeSave() plantel ≤ 26
    }
    class Sede {
        +Codigo* : %String S01 «único»
        +Estadio* : %String
        +Ciudad* : %String
        +Pais* : %String PATTERN 3U
        +Capacidad* : %Integer 1000..150000
    }
    class Partido {
        +Codigo* : %String P001 «único»
        +Fase* : grupos/.../final
        +FechaHora* : %TimeStamp
        +Estado* : PROGRAMADO/EN_JUEGO/FINALIZADO
        +Sede* : Sede «idx»
        +EquipoLocal* : Equipo «idx»
        +EquipoVisitante* : Equipo «idx»
        +ArbitroPrincipal* : Arbitro
        +Asistentes : list Of Arbitro (máx. 3)
        +Eventos : Relationship children
        +Iniciar() %Status
        +RegistrarEvento(tipo, minuto, jugador, evento) %Status
        +Finalizar() %Status
        +Marcador() %String
        +MinutoExpulsion(jugador) %String
        +TransicionValida(desde, hacia) %Boolean
        #%OnBeforeSave()
        trigger ReglasEstado()
        trigger ActaOficial()
    }
    class Evento {
        +Partido* : Partido «idx» (Relationship parent)
        +Tipo* : GOL/TARJETA_AMARILLA/TARJETA_ROJA/SUSTITUCION
        +Minuto* : %Integer 1..130
        +Jugador* : Jugador «idx»
        +Equipo* : Equipo
        +RegistradoEn* : %TimeStamp
        #%OnBeforeSave() equipo = equipo del jugador
        trigger SoloEnJuego()
        trigger Inalterable()
    }

    Persona <|-- Jugador
    Persona <|-- Arbitro
    Persona <|-- Tecnico

    Equipo "1" <--> "0..26" Jugador : Jugadores / Equipo
    Partido "1" *-- "0..*" Evento : Eventos / Partido (padre-hijo)

    Equipo --> "1" Tecnico : Tecnico
    Partido --> "1" Sede : Sede
    Partido --> "1" Equipo : EquipoLocal
    Partido --> "1" Equipo : EquipoVisitante
    Partido --> "1" Arbitro : ArbitroPrincipal
    Partido --> "0..3" Arbitro : Asistentes
    Evento --> "1" Jugador : Jugador
    Evento --> "1" Equipo : Equipo
```

## Tipos de asociación

| Asociación | Tipo en IRIS | Bidireccional | Qué implica |
|---|---|---|---|
| Persona → Jugador / Arbitro / Tecnico | Herencia (`Extends`) | — | Un solo extent: `Persona.%OpenId(id)` devuelve la subclase real; SQL tiene `Fixture.Persona` (todas) y una tabla por subclase. |
| Equipo ↔ Jugador | `Relationship` one / many | Sí | `equipo.Jugadores` y `jugador.Equipo` se mantienen sincronizados. Índice `EquipoIdx` en el lado "muchos". |
| Partido ↔ Evento | `Relationship` parent / children | Sí | Composición: el evento se guarda bajo el partido (ID `1\|\|3`), se guarda con él y se borra con él. |
| Partido → Sede, Equipo, Arbitro; Equipo → Tecnico; Evento → Jugador, Equipo | Referencia (`Property As Clase`) + `ForeignKey` | No | Navegable desde el objeto que referencia; la `ForeignKey` impide borrar lo referenciado. |
| Partido → Asistentes | `list Of Arbitro` | No | Grupo acotado (máx. 3). Una lista no admite `ForeignKey`: lo cubre el trigger `Arbitro.AsistenteEnPartido`. |

## Herencia y estado

Las subclases representan **tipos** que no cambian: un árbitro no se convierte en jugador.
El **estado** (programado, en juego, finalizado; expulsado) es un dato de la instancia, no una
subclase. Ver la nota de la consigna sobre "JugadorLesionado".
