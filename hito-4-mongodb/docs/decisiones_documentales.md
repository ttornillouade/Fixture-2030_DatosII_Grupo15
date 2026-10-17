# Grupo 15 — Hito 4 — Decisiones documentales del Fixture 2030

## 1. Objetivo y alcance

El Hito 2 eligió **MongoDB** para equipos y jugadores: cada ficha se consulta como una unidad
y el modelo documental admite variaciones sin un esquema rígido. El Hito 3 pidió que los cambios
oficiales mantengan una versión coherente del dato.

**Alcance corregido según el feedback:** el módulo guarda solo atributos propios de cada entidad.
Se quitaron `estadisticas` (goles, asistencias, atajadas) y `partidosInternacionales`, junto con
sus índices y consultas: son métricas deportivas y corresponden a su propio módulo.

## 2. Colecciones

### `equipos` (64 documentos)

| Campo | Tipo | Uso |
|---|---|---|
| `_id` | String `E001`–`E064` | Identificador estable, el mismo de los demás módulos |
| `nombre` | String | Nombre visible |
| `pais` | String | País representado |
| `confederacion` | Enum (AFC, CAF, CONCACAF, CONMEBOL, OFC, UEFA) | Filtro y agrupación |
| `grupo` | String `A`–`P` | Grupo del sorteo |
| `updatedAt` | Date | Fecha de alta del documento |

### `jugadores` (1.536 documentos)

| Campo | Tipo | Uso |
|---|---|---|
| `_id` | String `E001-J01` | Identificador estable, el mismo del Hito 5 |
| `equipoId` | String | Referencia a `equipos._id` |
| `nombre`, `apellido` | String | Datos personales |
| `fechaNacimiento` | Date | Dato personal |
| `nacionalidad` | String | Dato personal |
| `posicion` | Enum (Arquero, Defensor, Mediocampista, Delantero) | Filtro del plantel |
| `dorsal` | Int 1–99, único por equipo | Orden del plantel |
| `updatedAt` | Date | Fecha de alta del documento |

## 3. Tabla de decisiones

| Decisión | Alternativas consideradas | Elección | Justificación | Impacto esperado |
|---|---|---|---|---|
| Relación equipo–jugador | Embeber el plantel en el equipo / referencia desde el jugador | **Referencia `jugadores.equipoId → equipos._id`** | Los jugadores se consultan, filtran y paginan por separado; embebidos, cada cambio de un jugador reescribiría el documento del equipo | Documentos de equipo pequeños; consultas directas sobre jugadores; la integridad se controla con un script |
| Validación documental | Sin validación / `$jsonSchema` | **`$jsonSchema` estricto, sin campos adicionales** | El esquema flexible no reemplaza las reglas: ids, enums y rangos tienen que cumplirse siempre. `additionalProperties: false` impide volver a sumar métricas al documento | Se rechazan documentos incompletos o fuera de alcance |
| Identificadores | `ObjectId` / ids de negocio estables | **Ids de texto (`E001`, `E001-J01`)** | Carga idempotente y los mismos ids que Neo4j (Hito 5) y la API | Repetir la carga no duplica; las referencias entre módulos son legibles |
| Índices | Solo `_id` / índices por patrón de consulta | **`{equipoId, dorsal}` único y `{equipoId, posicion, dorsal}`** | El primero impide dorsales repetidos en un equipo; el segundo responde a la consulta principal (plantel por posición, ordenado por dorsal) | Menos documentos examinados; costo extra de escritura acotado a dos índices |
| Carga y actualización | `insertMany` / `updateOne` con `upsert` | **`bulkWrite` de `updateOne` + `upsert`; `updatedAt` con `$setOnInsert`** | La carga se puede repetir sin duplicados ni modificaciones innecesarias | La segunda carga informa 0 insertados y 0 modificados |
| Datos | Datos reales / sintéticos | **Sintéticos, los mismos CSV del Hito 5** | La consigna permite datos sintéticos; compartirlos hace coherentes los módulos | 64 equipos y 1.536 jugadores reproducibles |

## 4. Índice principal y rendimiento

Consulta: plantel de `E010` filtrado por `posicion = Delantero` y ordenado por `dorsal`
(pantalla de convocatoria). Resultado en la evidencia:

| | Índice usado | Documentos examinados | Claves examinadas | Devueltos |
|---|---|---|---|---|
| Antes | `equipo_dorsal_unico` | 24 | 24 | 7 |
| Después | `equipo_posicion_dorsal` | 7 | 7 | 7 |

Sin el índice compuesto, MongoDB filtra por equipo y lee todo el plantel para descartar las
otras posiciones; con él, lee exactamente los 7 delanteros, ya ordenados por dorsal.

## 5. Trazabilidad

- **Hito 2:** la ficha de equipo o jugador se lee como una unidad, sin joins.
- **Hito 3:** al no duplicar el plantel dentro del equipo, no hay dos versiones del mismo jugador
  que mantener cuando se agregue replicación.
- **Hito 5 y Hito 10:** los mismos ids permiten que el grafo y la API referencien a los mismos
  equipos y jugadores.

## 6. Limitaciones

- Una sola instancia local, sin replica set.
- La relación equipo–jugador no tiene FK automática: la controla `06_integridad.js`.
- Con este volumen, los tiempos absolutos son mínimos; se comparan documentos y claves examinados.
