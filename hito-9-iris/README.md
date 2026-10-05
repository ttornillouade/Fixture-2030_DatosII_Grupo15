# Grupo 15 — Hito 9 — Entidades complejas del Fixture 2030 (InterSystems IRIS)

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

Dominio estructural del partido del Fixture 2030 como clases persistentes de IRIS: el partido
es una máquina de estados con eventos inalterables, equipos con su plantel, árbitros y sede.
La consistencia la garantizan las propias clases (relaciones, tipos, índices, métodos y
triggers), sin ORM ni middleware, y vale tanto por objetos como por SQL.

## Resumen

```text
Motor:       InterSystems IRIS Community (intersystems/iris-community:latest-cd)
             observado: IRIS 2026.2 (Build 221U) — ver docs/evidencia/
Datos:       ~/docker/data/iris  (Durable %SYS)
Namespace:   USER   |   Paquete: Fixture   |   Esquema SQL: Fixture

Herencia:    Persona (abstracta) -> Jugador, Arbitro, Tecnico
Padre-hijo:  Partido <-> Evento          (parent/children: se guardan y borran juntos)
Uno-muchos:  Equipo  <-> Jugador         (one/many, índice EquipoIdx)
Estados:     PROGRAMADO -> EN_JUEGO -> FINALIZADO   (Partido.TransicionValida)
```

Resultado de la demostración: **45 de 45 pruebas con el resultado esperado** (cargas válidas
aceptadas y cargas inválidas rechazadas con el mensaje de IRIS).

## Estructura

```text
hito-9-iris/
├── docker-compose.yml          IRIS + Durable %SYS en ~/docker/data/iris
├── .env.example                contraseña local y puertos (copiar a .env)
├── src/Fixture/                código fuente del dominio (.cls)
│   ├── Persona.cls             clase base abstracta (herencia)
│   ├── Jugador.cls  Arbitro.cls  Tecnico.cls
│   ├── Equipo.cls  Sede.cls
│   ├── Partido.cls             máquina de estados, métodos y triggers
│   ├── Evento.cls              hijo de Partido, inalterable
│   └── Demo.cls                demostración invocable desde la terminal
├── sql/consultas.sql           consultas relacionales clásicas (RF8)
├── scripts/
│   ├── inicializacion.sh       levanta IRIS, aplica la contraseña y compila (RF1)
│   ├── cargar_clases.sh        copia src/ al contenedor y compila (RNF2)
│   ├── demo.sh                 ejecuta Fixture.Demo (RF5–RF9)
│   ├── bloque_terminal.sh      bloque de comandos del punto 5.3
│   ├── consultas_sql.sh        sql/consultas.sql en el shell SQL de IRIS
│   ├── generar_evidencia.sh    todo lo anterior + prueba de persistencia
│   ├── terminal.sh             terminal interactiva de IRIS
│   ├── limpieza.sh             limpieza opcional, con confirmación
│   └── iris/                   scripts que corren dentro del contenedor
└── docs/
    ├── diagrama_objetos.md     diagrama de clases (Mermaid)
    ├── matriz_integridad.md    reglas, mecanismos y qué pasa al borrar
    ├── decisiones_y_mejoras.md decisiones, ⚠️ challenges y mejoras propuestas
    ├── checklist_requisitos.md cada requisito de la consigna → dónde se cumple
    ├── coherencia_tpo.md       relación con los hitos anteriores
    └── evidencia/              salida real de la ejecución
```

## Operativa

Requisitos: Docker Desktop (o Docker Engine con Compose v2) y unos 4 GB libres para la imagen.
Todos los comandos se ejecutan desde esta carpeta (`hito-9-iris/`).

### 1. Configurar la contraseña local

```bash
cp .env.example .env
```

Editar `.env` y reemplazar `IRIS_PASSWORD`. Reemplaza la contraseña por defecto de la imagen
(`SYS`) en los usuarios `_SYSTEM`, `SuperUser` y `Admin`. `.env` no se versiona.

### 2. Levantar IRIS, cargar y compilar las clases

```bash
bash scripts/inicializacion.sh
```

Crea `~/docker/data/iris`, ejecuta `docker compose up -d`, espera a que IRIS acepte sesiones,
copia `src/` al contenedor y compila. Debe terminar con `Errores de compilación: 0` y
`COMPILACION OK`, y muestra la versión observada de IRIS.

En Linux, si IRIS no puede escribir en la carpeta de datos:
`sudo chown -R 51773:51773 ~/docker/data/iris` (ver
[challenge 2.4](docs/decisiones_y_mejoras.md#24-permisos-de-dockerdatairis)).

### 3. Ejecutar la demostración

```bash
bash scripts/demo.sh
```

Equivale a `do ##class(Fixture.Demo).Ejecutar()` en la terminal de IRIS. Cada sección se
puede correr por separado: `bash scripts/demo.sh CargarArbol`, `Navegar`, `FallasControladas`,
`ReglasDeEstado`, `ProyeccionSQL`, `Integridad`. `Ejecutar` empieza con `Limpiar`, así que se
puede repetir.

### 4. Instanciar y navegar a mano en la terminal

```bash
bash scripts/terminal.sh
```

Bloque de comandos del punto 5.3 (también en `scripts/iris/bloque_5_3.txt`, que se ejecuta
completo con `bash scripts/bloque_terminal.sh`):

```objectscript
// a) Estado al padre, luego al hijo, y un solo %Save del padre
do ##class(Fixture.Demo).Limpiar()
set sede = ##class(Fixture.Demo).NuevaSede("S01", "Estadio Centenario", "Montevideo", "URY", 60235)
set e1 = ##class(Fixture.Demo).NuevoEquipo("E001", "Seleccion 001", "Pais 001", "CONMEBOL", "A", "URY", 11, .j)
set e2 = ##class(Fixture.Demo).NuevoEquipo("E002", "Seleccion 002", "Pais 002", "UEFA", "A", "ESP", 11, .j)
set p = ##class(Fixture.Partido).%New()
set p.Codigo = "P001", p.Fase = "grupos", p.FechaHora = "2030-06-08 16:00:00"
set p.Sede = sede, p.EquipoLocal = e1, p.EquipoVisitante = e2
set p.ArbitroPrincipal = ##class(Fixture.Demo).NuevoArbitro("A01", "FIFA", "ARG")
write p.Iniciar()                                        // 1: PROGRAMADO -> EN_JUEGO
write p.RegistrarEvento("GOL", 23, j("E001J09"), .gol)   // 1: hijo agregado en memoria
write "'", p.%Id(), "' '", gol.%Id(), "'"                // '' '': nada guardado todavía
write p.%Save()                                          // 1: una sola invocación
write p.%Id(), " ", gol.%Id(), " ", sede.%Id()           // 1 1||1 1: todo el árbol persistido

// Navegación por referencias (sin SQL)
write p.Sede.Estadio, " / ", p.EquipoLocal.Tecnico.NombreCompleto(), " / ", p.Marcador()
write gol.Partido.Codigo, " ", gol.Jugador.Equipo.Jugadores.Count()

// b) Falla controlada: propiedad requerida omitida
set x = ##class(Fixture.Arbitro).%New()
set x.Nombre = "Sin", x.Apellido = "Licencia", x.Documento = "DOC-X", x.FechaNacimiento = $ZDATEH("1990-01-01", 3), x.Nacionalidad = "URY", x.Categoria = "FIFA"
do $SYSTEM.Status.DisplayError(x.%Save())                // ERROR #5659: Property ... Licencia ... required

// Transición ilegal (ejemplo de la consigna)
do p.Finalizar()
do $SYSTEM.Status.DisplayError(p.RegistrarEvento("GOL", 0, j("E001J09")))   // partido FINALIZADO

// c) Los mismos datos por SQL
do $SYSTEM.SQL.Shell()
SELECT Codigo, Estado, Sede->Estadio, EquipoLocal->Codigo FROM Fixture.Partido
SELECT ID, Minuto, Tipo, Jugador->Codigo FROM Fixture.Evento
quit
```

### 5. Consultas SQL relacionales

```bash
bash scripts/consultas_sql.sh
```

Ejecuta [`sql/consultas.sql`](sql/consultas.sql) en el shell SQL de IRIS: tablas del esquema,
herencia en `Fixture.Persona`, joins implícitos (`->`) y explícitos, marcador y tarjetas por
SQL. También se puede usar el Portal (`http://localhost:52773/csp/sys/UtilHome.csp`, usuario
`_SYSTEM` y la contraseña de `.env`) en *System Explorer → SQL*.

### 6. Generar la evidencia

```bash
bash scripts/generar_evidencia.sh
```

Escribe `docs/evidencia/evidencia_hito9_<fecha>.txt`. Ver [docs/evidencia/README.md](docs/evidencia/README.md).

### 7. Detener y reiniciar sin perder datos

```bash
docker compose down
docker compose up -d
bash scripts/demo.sh Navegar
```

Los datos y las clases compiladas viven en `~/docker/data/iris`: el contenedor nuevo los
encuentra (verificado en la sección 5 de la evidencia). Solo hace falta
`bash scripts/cargar_clases.sh` después de modificar un `.cls`.

### 8. Limpieza (opcional)

```bash
bash scripts/limpieza.sh --datos
```

Borra los objetos de la demo y deja las clases. `--reset-total` detiene el contenedor e
indica cómo borrar `~/docker/data/iris`. Ambos piden confirmación.

## Documentación

| Apartado de la consigna | Documento |
|---|---|
| Diagrama de objetos | [docs/diagrama_objetos.md](docs/diagrama_objetos.md) |
| Matriz de integridad (¿qué pasa con los eventos si se borra un partido?) | [docs/matriz_integridad.md](docs/matriz_integridad.md) |
| Código fuente de dominio | [src/Fixture/](src/Fixture/) |
| Operativa | esta sección |
| Evidencia de ejecución | [docs/evidencia/](docs/evidencia/) |
| Decisiones y ⚠️ challenges | [docs/decisiones_y_mejoras.md](docs/decisiones_y_mejoras.md) |
| Checklist de requisitos | [docs/checklist_requisitos.md](docs/checklist_requisitos.md) |
| Coherencia con el TPO | [docs/coherencia_tpo.md](docs/coherencia_tpo.md) |

## ⚠️ Puntos a discutir (resumen)

El detalle está en [docs/decisiones_y_mejoras.md](docs/decisiones_y_mejoras.md).

1. **RNF3 en padre-hijo:** IRIS guarda los eventos debajo del partido y no usa `PartidoIdx`
   (el plan de ejecución lo muestra). Se mantiene por la consigna; se propone quitarlo.
2. **`latest-cd` cambia con el tiempo:** la evidencia registra versión y digest; se propone
   fijar la imagen por digest.
3. **El código se copia (`docker cp`) en lugar de montarse,** para que funcione aunque el
   proyecto esté en Escritorio o Documentos de macOS.
4. **Permisos del instructivo docente:** no estaban disponibles; en Linux, UID 51773.
5. **Eventos inalterables sin forma de corregir** (gol anulado): se propone un evento compensatorio.
6. **Asistentes como lista:** sin `ForeignKey` posible; se cerró el hueco con un trigger y se
   propone una clase `Designacion`.
7. **Tres reglas solo valen por objetos** (plantel ≤ 26, asistentes ≤ 3, equipo del evento).

## Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| `docker compose up` queda colgado y el contenedor en `Created` | Un intento anterior quedó a medias. `docker rm -f fixture2030-iris`, `docker network rm hito-9-iris_default` y repetir. Si se agregó un montaje de una carpeta del proyecto en Escritorio/Documentos, macOS espera un permiso: ver [challenge 2.3](docs/decisiones_y_mejoras.md#23-el-código-se-copia-al-contenedor-en-lugar-de-montarse). |
| `Falta .env` | `cp .env.example .env` y definir `IRIS_PASSWORD`. |
| Los acentos se ven como `�` en una sesión propia | La terminal por `docker exec` no usa UTF-8: `do ##class(%SYS.NLS.Device).SetIO("UTF8")`. Los scripts ya lo hacen. |
| `Permission denied` en `/durable/iris` (Linux) | `sudo chown -R 51773:51773 ~/docker/data/iris`. |
| Cambié un `.cls` y no se refleja | `bash scripts/cargar_clases.sh`. |
