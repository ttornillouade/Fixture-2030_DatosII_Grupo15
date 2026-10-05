# Decisiones, puntos a discutir y mejoras

Este documento separa tres cosas:

- **Decisiones**: lo que se eligió y por qué.
- **⚠️ Challenge**: puntos donde la consigna, la herramienta o el modelo admiten otra lectura,
  o donde cumplir al pie de la letra no es lo óptimo. Se explica qué se hizo y qué se propone.
- **Mejoras propuestas**: lo que quedó fuera del alcance y se haría en una versión siguiente.

Todo lo afirmado se puede verificar en [`evidencia/`](evidencia/).

---

## 1. Decisiones principales

| Tema | Decisión | Motivo |
|---|---|---|
| Porción del dominio | Partido (máquina de estados) con sus Eventos, Equipos con Jugadores y Técnico, Árbitros y Sede | Es la porción que la consigna describe como "máquina de estado compleja" y concentra las reglas de integridad del fixture. |
| Herencia | `Persona` abstracta → `Jugador`, `Arbitro`, `Tecnico` | Tres tipos inmutables con datos comunes. El estado (expulsado, partido finalizado) es dato, no subclase. |
| Padre-hijo | `Partido` ↔ `Evento` (`parent`/`children`) | Un evento no existe sin su partido: es composición. Se guarda con el partido y se borra con él. |
| Uno a muchos | `Equipo` ↔ `Jugador` (`one`/`many`, `OnDelete = noaction`) | El jugador existe por sí mismo, pero no se puede borrar un equipo con plantel. |
| Reglas | Métodos + `%OnBeforeSave` + triggers `row/object` | La proyección SQL no puede saltear la máquina de estados (ver [matriz_integridad.md](matriz_integridad.md#por-qué-tres-niveles)). |
| Identificadores | `E001`, `E001J09`, `P001`, `S01` | Los mismos de los hitos anteriores (ver [coherencia_tpo.md](coherencia_tpo.md)). |
| Demo | Clase `Fixture.Demo` invocable desde la terminal | RNF4: todo es `.cls` e invocable desde la terminal; la demo se repite con el mismo resultado. |

---

## 2. ⚠️ Challenges

### 2.1 RNF3 pide un índice que IRIS no usa en la relación padre-hijo

**Consigna:** "la clase en el extremo muchos debe incluir un índice sobre la propiedad
relacional".

**Qué pasa en IRIS:** en una relación `parent`/`children`, los hijos se guardan **debajo** del
padre (el ID del evento es `partido||childsub`). Buscar los eventos de un partido ya es un
acceso directo por clave. El plan de ejecución lo confirma:

```text
SELECT Minuto FROM Fixture.Evento WHERE Partido = 1
  Read master map Fixture.Evento.IDKEY, using the given Partido, and looping on childsub.
```

El índice `Evento.PartidoIdx` **no aparece en el plan**: solo agrega una escritura por evento.

**Qué se hizo:** se mantiene `PartidoIdx` para cumplir RNF3 al pie de la letra. En la relación
uno a muchos (`Equipo` ↔ `Jugador`) el índice sí es necesario y el plan muestra que se usa
(`Read index map Fixture.Jugador.EquipoIdx`).

**Propuesta:** consultar con el docente si RNF3 aplica a relaciones padre-hijo. Si no aplica,
quitar `PartidoIdx`.

### 2.2 `latest-cd` es un tag que cambia

**Consigna:** `intersystems/iris-community:latest-cd`.

**Riesgo:** `latest-cd` (Continuous Delivery) apunta a una versión nueva cada pocos meses. Es el
mismo problema que tuvo el Hito 8 con `influxdb:latest`: la versión que ejecute el docente
puede no ser la probada.

**Qué se hizo:** se usa el tag pedido y la evidencia registra la versión observada
(IRIS 2026.2, build 221U) y el digest de la imagen.

**Propuesta:** para una corrida reproducible, fijar la imagen por digest
(`intersystems/iris-community@sha256:...`, el que figura en la evidencia).

### 2.3 El código se copia al contenedor en lugar de montarse

**Consigna (5.1):** "la carga inicial del código a la máquina virtual debe poder automatizarse
o ejecutarse fácilmente".

**Problema encontrado:** montar `./src` desde un proyecto ubicado en Escritorio o Documentos
deja a `docker compose up` esperando un permiso de privacidad de macOS, sin mensaje de error.

**Qué se hizo:** el compose solo monta `~/docker/data/iris`. `scripts/cargar_clases.sh` copia
`src/` con `docker cp` y compila. `scripts/inicializacion.sh` lo hace automáticamente.

**Consecuencia:** después de editar un `.cls` hay que ejecutar `bash scripts/cargar_clases.sh`.
Las clases compiladas quedan en la base `USER` dentro de `~/docker/data/iris`, así que un
`docker compose up -d` posterior no necesita recompilar (verificado en la evidencia, sección 5).

### 2.4 Permisos de `~/docker/data/iris`

**Consigna:** "con los permisos que indica el instructivo docente".

El instructivo no estaba disponible al implementar. En macOS con Docker Desktop no hizo falta
cambiar permisos. En Linux, el proceso de IRIS corre como `irisowner` (UID 51773) y la carpeta
necesita ese dueño:

```bash
sudo chown -R 51773:51773 ~/docker/data/iris
```

**Propuesta:** contrastar con el instructivo docente y ajustar el README si indica otra cosa.

### 2.5 Eventos inalterables frente a correcciones reales

La consigna pide eventos "inalterables". En un partido real hay correcciones (un gol anulado
por el VAR). Hoy un evento registrado no se puede modificar ni borrar suelto, así que
**no hay forma de corregir un error de carga** salvo borrar el partido completo (si no está
finalizado).

**Propuesta:** un evento compensatorio (`GOL_ANULADO`, que referencia al gol original) que
mantenga el historial *append-only* y que `Marcador()` descuente.

### 2.6 Borrar un partido no finalizado borra sus eventos

Es lo que implica la composición padre-hijo y responde a la pregunta de la matriz de
integridad. Se aceptó para el caso "partido cargado por error".

**Propuesta:** en producción, preferir una baja lógica (estados `SUSPENDIDO` y `CANCELADO`
en la máquina de estados) y reservar el borrado físico para administración.

### 2.7 Los asistentes son una lista y no una clase

`Partido.Asistentes` es `list Of Arbitro`: simple y suficiente para "un grupo delimitado de
árbitros", pero una lista **no admite `ForeignKey`**. Durante las pruebas se comprobó que se
podía borrar un árbitro asistente y dejar al partido con una referencia rota.

**Qué se hizo:** el trigger `Arbitro.AsistenteEnPartido` impide ese borrado por objetos y por
SQL (por `Arbitro` y por `Persona`). Está en la demo y en la evidencia.

**Propuesta:** modelar `Designacion` como hija de `Partido` (rol `PRINCIPAL`, `ASISTENTE`,
`CUARTO`) con `ForeignKey` e índice sobre el árbitro. Así se puede consultar "partidos de un
árbitro" por índice y la integridad la da el motor, no un trigger.

### 2.8 "Alineación" se valida con el plantel

`Iniciar()` exige que cada equipo tenga al menos 11 jugadores en el plantel. No modela qué
11 son titulares.

**Propuesta:** una clase `Alineacion` hija de `Partido` con los 11 titulares por equipo y
validación de un solo arquero.

---

## 3. Reglas que solo valen por objetos

Tres reglas de la [matriz](matriz_integridad.md) están en `%OnBeforeSave`, que no se ejecuta
en `INSERT`/`UPDATE` por SQL:

| Regla | Dónde está | Para que valga por SQL |
|---|---|---|
| Plantel de hasta 26 jugadores | `Equipo.%OnBeforeSave` | Trigger `INSERT` en `Jugador` que cuente el plantel del equipo. |
| Hasta 3 asistentes, sin repetir al principal | `Partido.%OnBeforeSave` | Agregarlo al trigger `ReglasEstado`. Con la clase `Designacion` (2.7) sería un trigger sobre ella. |
| Equipo del evento = equipo del jugador | `Evento.%OnBeforeSave` | Agregarlo al trigger `SoloEnJuego`. |

No se movieron a triggers para no duplicar código antes de acordar el modelo de
`Designacion`. Las reglas críticas (estado, eventos inalterables, acta oficial, borrados)
ya valen por SQL.

---

## 4. Mejoras propuestas

| Mejora | Beneficio |
|---|---|
| Namespace y base de datos propios (`FIXTURE`) en lugar de `USER` | Aislamiento del resto de la instancia; el `.gitignore` y la limpieza serían por base. |
| Tests con `%UnitTest` además de la demo | La demo informa "esperado/inesperado"; `%UnitTest` daría un reporte estándar e integrable en CI. |
| Fijar la imagen por digest (2.2) | Reproducibilidad. |
| Clases `Designacion` y `Alineacion` (2.7, 2.8) | Integridad dada por el motor y alineaciones reales. |
| Evento compensatorio (2.5) | Correcciones sin romper la inmutabilidad. |
| `TuneTable` después de la carga | El plan avisa "Table ... is not tuned"; con estadísticas el optimizador elige mejor en tablas grandes. |
