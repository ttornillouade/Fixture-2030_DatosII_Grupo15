# Comparación con una alternativa relacional (RF14, 5.6)

> **Análisis conceptual.** No se hizo una comparación experimental contra una base relacional: el equipo no
> tiene en el laboratorio un PostgreSQL/MySQL con la misma carga, datos y hardware, y comparar una base
> instalada "a mano" contra Cassandra en Docker no sería una comparación válida. Los números citados acá
> son los **medidos sobre Cassandra** en este hito; lo que se dice de la alternativa relacional es
> razonamiento, no medición.

## El flujo comparado

"Comentarios en vivo": leer la primera página (20 más recientes) de la ventana de 5 minutos actual de un
partido, y publicar comentarios, con 60 usuarios concurrentes y una proporción 90 % lectura / 10 % escritura.

## Cómo sería en un modelo relacional

**Unidad de información**: una fila por comentario en una tabla normalizada.

```sql
CREATE TABLE comentario (
  comentario_id   VARCHAR(16) PRIMARY KEY,
  partido_id      VARCHAR(4)  NOT NULL REFERENCES partido(partido_id),
  autor_id        VARCHAR(7)  NOT NULL REFERENCES usuario(usuario_id),
  creado_en       TIMESTAMP   NOT NULL,
  contenido       VARCHAR(500) NOT NULL,
  estado_moderacion VARCHAR(10) NOT NULL,
  reacciones      INT NOT NULL DEFAULT 0
);
-- La consulta del feed necesita este índice compuesto (sin él, escanea todos los comentarios del partido):
CREATE INDEX ix_comentario_feed ON comentario (partido_id, creado_en DESC, comentario_id DESC);
-- La vista "mis comentarios" (la segunda tabla de Cassandra) es solo otro índice:
CREATE INDEX ix_comentario_autor ON comentario (autor_id, creado_en DESC);
```

**Operaciones**:

| Operación | Cassandra (implementado) | Relacional (alternativa) |
|---|---|---|
| Primera página | 8 consultas `SELECT ... WHERE partido, bucket, shard LIMIT 21` en paralelo + fusión en la API | 1 consulta `SELECT ... WHERE partido_id=? AND creado_en >= ? ORDER BY creado_en DESC LIMIT 21` sobre el índice |
| Página siguiente | igual, con `(creado_en, id) < cursor` en cada shard | igual, con `(creado_en, comentario_id) < (?, ?)` (keyset) |
| Publicar | `BATCH LOGGED` de 2 inserts (por partido y por usuario) | 1 `INSERT` en una transacción; el índice por autor se actualiza solo |
| "Mis comentarios" | lectura directa de `comentarios_por_usuario` | la misma tabla, por el índice `ix_comentario_autor` |

**Qué es más simple en relacional**: la lectura (una consulta en lugar de 8 + fusión en la API), la
paginación y la consistencia de la segunda vista (es un índice, no una tabla duplicada que hay que
mantener con un batch). El esquema es uno solo y se pueden hacer consultas no previstas (`GROUP BY`,
joins con partido y usuario) sin crear tablas nuevas.

**Qué es más complejo en relacional**: escalar las escrituras. Todas las inserciones de un partido caliente
van al **final del mismo índice** (`partido_id, creado_en`): es un punto caliente de escritura en un solo
nodo primario. Para crecer más allá de un servidor hay que particionar (por partido o por fecha) y la
aplicación o una capa de sharding pasa a decidir a qué nodo ir: exactamente lo que Cassandra resuelve con
la clave de partición `(partido_id, bucket_5m, shard)` y el anillo de tokens.

## Garantías esperadas

| | Cassandra (como está configurado) | Relacional |
|---|---|---|
| Escritura de un comentario | Durable en el nodo (commitlog); en el laboratorio RF=1. Las dos tablas, juntas por `BATCH LOGGED` (atomicidad eventual, sin aislamiento) | ACID: ambos índices se actualizan en la misma transacción |
| Lectura después de escribir | Con un nodo, inmediata. Con RF=3 y `ONE/ONE`, eventual; con `QUORUM/QUORUM`, se lee lo escrito | Inmediata en el primario; eventual en réplicas de lectura |
| Ante la caída de un nodo | Con RF=3 y `LOCAL_QUORUM`, sigue aceptando lecturas y escrituras (AP con consistencia ajustable) | Si cae el primario, las escrituras esperan la conmutación por error (segundos a minutos) |

Para comentarios, la regla de negocio tolera que un comentario aparezca uno o dos segundos tarde, pero no
tolera que el feed deje de aceptar comentarios durante un partido. Eso inclina la balanza hacia la
disponibilidad (Cassandra), no hacia la consistencia fuerte.

## Cómo crecerían volumen y concurrencia

- **Volumen almacenado**: en Cassandra el costo de leer una página no cambia con el total del partido
  (la partición es de 5 minutos y 1/8 de los comentarios). En relacional tampoco, mientras el índice
  `(partido_id, creado_en)` esté en memoria; con cientos de millones de filas el índice crece y hay que
  particionar la tabla por fecha.
- **Concurrencia de lectura**: la medición de este hito mostró que, con 60 usuarios, el límite **no fue
  Cassandra sino el proceso de la API** (1 núcleo al 90 %; ver `linea_base.md`). La lectura de 8 shards
  cuesta más CPU en la API que una sola consulta relacional, porque hay 8 respuestas para decodificar y
  fusionar. **En este escenario, un modelo relacional probablemente habría tenido un costo de lectura
  por request menor** (dato no medido).
- **Concurrencia de escritura**: es donde el diseño de Cassandra paga. Con 8 shards por ventana, las
  escrituras de un partido caliente se reparten en 8 particiones (y, con varios nodos, en varios nodos).
  En el laboratorio (un nodo, ~16 escrituras/s) esa ventaja **no se ve**: es una propiedad de diseño, no
  un resultado medido.

## En qué condición conviene cada una

**Conviene NoSQL (Cassandra) cuando**: el volumen de escrituras de un mismo partido supera lo que acepta
un primario relacional; se necesita seguir escribiendo aunque caiga un nodo o una región; los accesos
están acotados y se conocen de antemano (feed por partido y ventana, comentarios de un usuario); y se
acepta consistencia eventual en la lectura.

**Conviene relacional cuando**: el volumen cabe en un primario con réplicas (por ejemplo, torneos más chicos
o solo moderación interna); se necesitan consultas ad hoc o transacciones que abarquen comentario,
usuario y moderación; o el equipo prioriza simplicidad operativa sobre escalabilidad horizontal.

**Combinación razonable para el Fixture**: Cassandra para el camino operacional (escritura y feed en vivo)
y una proyección relacional/analítica alimentada por ETL para las preguntas agregadas (`integracion_data_mart.md`).

## Qué no se pudo medir en el laboratorio

- El rendimiento de una base relacional con la misma carga (no hay comparación experimental).
- El comportamiento con varios nodos de Cassandra (RF=3, consistencia `QUORUM`, caída de un nodo).
- El punto caliente de escritura de un índice relacional con miles de inserciones por segundo.
- La latencia entre regiones.
