# Checklist de requisitos — Hito 9

## Requisitos funcionales

| ID | Requisito | Dónde se cumple | Evidencia |
|---|---|---|---|
| RF1 | IRIS local en Docker con persistencia | `docker-compose.yml` (Durable %SYS en `~/docker/data/iris`), `scripts/inicializacion.sh` | Secciones 1 y 5 (datos intactos tras `down` + `up`) |
| RF2 | Al menos 3 entidades principales | 8 clases persistentes: `Persona`, `Jugador`, `Arbitro`, `Tecnico`, `Equipo`, `Sede`, `Partido`, `Evento` | [diagrama_objetos.md](diagrama_objetos.md) |
| RF3 | Relación padre-hijo o uno a muchos con integridad bidireccional | `Partido` ↔ `Evento` (parent/children) y `Equipo` ↔ `Jugador` (one/many) | Navegación inversa evento → partido → sede y jugador → equipo → jugadores |
| RF4 | Herencia desde una clase base en 2+ entidades | `Persona` → `Jugador`, `Arbitro`, `Tecnico` | `Persona.%OpenId(id)` devuelve la subclase; `x__classname` en SQL |
| RF5 | Propiedades obligatorias y tipos estrictos | `[Required]`, `VALUELIST`, `MINVAL/MAXVAL`, `PATTERN`, `MAXLEN`, índices únicos | Sección "RF5 - Fallas de carga controladas" |
| RF6 | Árbol padre-hijo guardado con un solo `%Save` | `Fixture.Demo.CargarArbol()` y bloque 5.3 a) | Ids vacíos antes y asignados después de `p.%Save()` |
| RF7 | Consulta navegando referencias, sin SQL | `Fixture.Demo.Navegar()`, `Partido.Marcador()` | Sección "RF7" |
| RF8 | Los mismos datos por SQL relacional | `sql/consultas.sql` (shell SQL), `Fixture.Demo.ProyeccionSQL()` | Secciones 3 y 4; `INSERT`/`UPDATE` por SQL visibles como objetos |
| RF9 | Validación encapsulada que impide una transición ilegal | `Partido.Iniciar/RegistrarEvento/Finalizar`, triggers `ReglasEstado`, `SoloEnJuego`, `Inalterable`, `ActaOficial` | "Gol en el minuto 0 en P001 FINALIZADO" (ejemplo de la consigna) y los demás casos de la sección RF9 |

## Requisitos no funcionales

| ID | Requisito | Dónde se cumple |
|---|---|---|
| RNF1 | `docker compose` oficial y `~/docker/data/iris` | `docker-compose.yml` |
| RNF2 | Compila sin errores ni dependencias no declaradas | `scripts/cargar_clases.sh` (sale con error si algo no compila). Evidencia: `Errores de compilación: 0` |
| RNF3 | Índice sobre la propiedad relacional del lado "muchos" | `Jugador.EquipoIdx`, `Evento.PartidoIdx`. Plan de ejecución en la evidencia. Ver [challenge 2.1](decisiones_y_mejoras.md#21-rnf3-pide-un-índice-que-iris-no-usa-en-la-relación-padre-hijo) |
| RNF4 | Todo en `.cls` e invocable desde la terminal | `src/Fixture/*.cls`; `do ##class(Fixture.Demo).Ejecutar()`; `scripts/terminal.sh` |
| RNF5 | Repositorio GitHub con historial | Enlace al inicio del README; commits por etapa en la rama `feature_hito_9` |

## Especificación técnica

| Punto | Cumplimiento |
|---|---|
| 5.1 Compose con `iris-community:latest-cd`, Durable %SYS, carga del código automatizable | `docker-compose.yml` + `scripts/inicializacion.sh` (ver [challenge 2.3](decisiones_y_mejoras.md#23-el-código-se-copia-al-contenedor-en-lugar-de-montarse)) |
| 5.2 `[Required]` y tipos fijos | Todas las clases |
| 5.2 `Relationship` con `parent`/`children`/`one`/`many` | `Partido.Eventos`, `Evento.Partido`, `Equipo.Jugadores`, `Jugador.Equipo` |
| 5.2 Índices explícitos en los lados hijos | `EquipoIdx`, `PartidoIdx`, `JugadorIdx` |
| 5.2 `%OnBeforeSave` (opcional) | `Partido`, `Equipo`, `Evento` |
| 5.3 Bloque de comandos: padre → hijo → un `%Save` | `scripts/iris/bloque_5_3.txt` (a) |
| 5.3 Falla controlada por propiedad requerida omitida | Bloque 5.3 (b): árbitro sin `Licencia` |
| 5.3 Tablas SQL coinciden con los objetos | Bloque 5.3 (c) y sección RF8 |

## Restricciones

| Restricción | Cumplimiento |
|---|---|
| Íntegramente en IRIS, sin ORM | Solo clases ObjectScript y SQL de IRIS; los scripts `bash` únicamente invocan la terminal. |
| Persistencia en `~/docker/data/iris` | Montaje del compose |
| Sin binarios ni datos de la base en el repositorio | `.gitignore` (`.env`, `*.DAT`, `iris.cpf`, `journal/`, `durable/`); los datos viven fuera del proyecto |

## Estructura esperada del análisis (sección 8)

| Apartado | Documento |
|---|---|
| Diagrama de objetos | [diagrama_objetos.md](diagrama_objetos.md) |
| Matriz de integridad | [matriz_integridad.md](matriz_integridad.md) |
| Código fuente de dominio | [`src/Fixture/`](../src/Fixture/) |
| Operativa | [README.md](../README.md#operativa) |
| Evidencia de ejecución | [evidencia/](evidencia/) |
