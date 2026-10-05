# Matriz de integridad

Cada regla está implementada **dentro de las clases** (sin ORM ni middleware). La columna
"SQL" indica si la regla también se cumple cuando se opera por la proyección SQL: es la
diferencia entre una validación de objeto (`%OnBeforeSave`, métodos) y una del motor
(tipos, índices, `ForeignKey`, triggers `Foreach = row/object`).

La columna "Evidencia" remite a la salida de `do ##class(Fixture.Demo).Ejecutar()` en
[`evidencia/`](evidencia/).

## ¿Qué ocurre con los eventos si un partido se borra?

| Estado del partido | Resultado | Mecanismo |
|---|---|---|
| `PROGRAMADO` o `EN_JUEGO` | Se borra el partido **y todos sus eventos** en cascada. | `Relationship ... Cardinality = parent`: el evento es parte del partido. |
| `FINALIZADO` | **No se puede borrar**: es el acta oficial. Partido y eventos quedan intactos. | Trigger `Partido.ActaOficial` (objetos y SQL). |

Los eventos no se pueden borrar **ni modificar** sueltos para cambiar el resultado: el
`UPDATE` está bloqueado (trigger `Evento.Inalterable`) y un jugador con eventos no se puede
borrar (`Evento.JugadorFK`).

## Reglas

| # | Regla | Mecanismo | Objetos | SQL | Evidencia |
|---|---|---|---|---|---|
| 1 | Toda propiedad marcada `*` es obligatoria | `[Required]` | ✅ | ✅ | Jugador sin Documento; árbitro sin Licencia (5.3 b) |
| 2 | Tipos estrictos: enumerados, rangos, formatos | `VALUELIST`, `MINVAL/MAXVAL`, `PATTERN`, `MAXLEN` | ✅ | ✅ | Posición LIBERO, dorsal 120, nacionalidad `ury`, sede con Pais `Uruguay` por SQL |
| 3 | Códigos únicos (`E001`, `P001`, `E001J09`, documento, licencia) | `Index ... [Unique]` | ✅ | ✅ | — |
| 4 | Un dorsal no se repite en el mismo equipo | `Index EquipoDorsalIdx On (Equipo, Dorsal) [Unique]` | ✅ | ✅ | Dorsal 9 repetido en E001 |
| 5 | Un técnico dirige un solo equipo | `Index TecnicoIdx On Tecnico [Unique]` | ✅ | ✅ | — |
| 6 | Plantel de hasta 26 jugadores | `Equipo.%OnBeforeSave` | ✅ | ❌ (ver mejoras) | — |
| 7 | Un equipo con jugadores no se borra | `Relationship Equipo [OnDelete = noaction]` | ✅ | ✅ | Borrar E004 con jugadores |
| 8 | No se borra una sede, equipo, árbitro principal o técnico en uso | `ForeignKey` | ✅ | ✅ | Borrar S01, árbitro A01, técnico de E001 |
| 9 | No se borra un árbitro asistente en uso | Trigger `Arbitro.AsistenteEnPartido` | ✅ | ✅ | Borrar árbitro A03 |
| 10 | No se borra un jugador con eventos | `ForeignKey Evento.JugadorFK` | ✅ | ✅ | Borrar E001J09 |
| 11 | Máquina de estados: solo `PROGRAMADO → EN_JUEGO → FINALIZADO` | `TransicionValida` usada por `Iniciar`/`Finalizar` y por el trigger `ReglasEstado` | ✅ | ✅ | Iniciar P001 finalizado; Finalizar P002 programado; `UPDATE ... SET Estado` |
| 12 | Un partido nuevo nace `PROGRAMADO` o `EN_JUEGO` | Trigger `ReglasEstado` (INSERT) | ✅ | ✅ | — |
| 13 | Para iniciar, cada equipo tiene al menos 11 jugadores | `Partido.Iniciar` | ✅ | — (es una operación) | P002 con E004 de 5 jugadores |
| 14 | Un equipo no juega contra sí mismo | `%OnBeforeSave` + trigger `ReglasEstado` | ✅ | ✅ | P009 = E003 vs E003 |
| 15 | Hasta 3 asistentes, sin repetir al árbitro principal | `Partido.%OnBeforeSave` | ✅ | ❌ (ver mejoras) | Árbitro principal como asistente |
| 16 | Solo se agregan eventos a partidos `EN_JUEGO` | `RegistrarEvento` + trigger `Evento.SoloEnJuego` | ✅ | ✅ | Gol en minuto 0 en P001 finalizado (ejemplo de la consigna); `Eventos.Insert`; `INSERT` SQL |
| 17 | El minuto va de 1 a 130 | `Minuto %Integer(MINVAL = 1, MAXVAL = 130)` | ✅ | ✅ | — |
| 18 | El jugador del evento juega ese partido | `RegistrarEvento` | ✅ | — | Evento de E004J01 en P003 |
| 19 | El equipo del evento es el del jugador | `Evento.%OnBeforeSave` | ✅ | ❌ (ver mejoras) | — |
| 20 | Un expulsado no tiene eventos posteriores | `RegistrarEvento` (`MinutoExpulsion`) | ✅ | — | Gol de E003J05 después de su roja |
| 21 | Un evento registrado es inalterable | Trigger `Evento.Inalterable` | ✅ | ✅ | `UPDATE Fixture.Evento SET Minuto = 1` |
| 22 | Un partido finalizado no se borra | Trigger `Partido.ActaOficial` | ✅ | ✅ | Borrar P001 |
| 23 | El árbol se guarda entero o no se guarda | Transacción del `%Save` (journaling de la base USER) | ✅ | ✅ | E003 con un jugador inválido; `%Save` con cambio de sede + evento ilegal |

`—` = la regla es parte de una operación de negocio (método), no de un cambio de datos.
`❌` = hoy solo se valida por objetos; está señalado como mejora en
[decisiones_y_mejoras.md](decisiones_y_mejoras.md#3-reglas-que-solo-valen-por-objetos).

## Por qué tres niveles

1. **Métodos** (`Iniciar`, `RegistrarEvento`, `Finalizar`): la forma normal de operar; dan
   mensajes de negocio claros.
2. **`%OnBeforeSave`**: valida el objeto completo cada vez que se guarda por objetos.
3. **Triggers `Foreach = row/object`**: se ejecutan tanto en `%Save`/`%Delete` como en
   `INSERT`/`UPDATE`/`DELETE`. Sin ellos, la proyección SQL (RF8) sería una puerta trasera
   para saltear la máquina de estados.

La lógica de transición está en un solo lugar (`Partido.TransicionValida`) y la usan los
métodos y el trigger.
