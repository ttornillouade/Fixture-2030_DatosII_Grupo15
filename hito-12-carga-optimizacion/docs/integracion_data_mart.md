# Integración analítica: Data Mart de actividad por partido (RF12, RF13, RNF12, 5.7)

## Pregunta analítica

> **¿Cómo evoluciona, minuto a minuto, la actividad de los hinchas durante cada partido, y qué momentos del
> partido (goles, tarjetas, cambios de posesión) la disparan?**

Sirve a la FIFA y a los medios para detectar los momentos de mayor interés, dimensionar la infraestructura
para partidos similares y moderar donde se concentra la actividad.

## Por qué no se responde consultando las fuentes operacionales

La respuesta necesita **todo** el partido (≈ 20-30 ventanas de 5 minutos × 8 shards = cientos de particiones de
Cassandra) y cruzarlo con eventos (IRIS), estadísticas (InfluxDB) y equipos (MongoDB). Hacerlo en cada consulta:

- compite con el camino operacional (las mismas particiones que lee el feed en vivo);
- encadena 4 bases en una request (si una falla o es lenta, falla la respuesta);
- repite el mismo cálculo para cada consulta, aunque los datos de un minuto cerrado ya no cambian.

**Medido en el laboratorio** (`evidencia/data_mart/comparacion_fuente_vs_mart.json`, 10 repeticiones, mismo
cliente Python, 2026-11-13): la misma pregunta "comentarios por minuto de P901" sobre 49 ventanas:

| | Fuente operacional (Cassandra) | Proyección (Data Mart) |
|---|---|---|
| Particiones leídas | 392 | 1 |
| Filas transferidas | 132.000 | 228 |
| Tiempo (mediana / máximo) | **686,9 / 782,9 ms** | **3,0 / 13,7 ms** |
| Respuesta | — | idéntica (`mismas_respuestas: true`) |

## Fuentes, atributos y procedencia

| Fuente operacional | Dato | Atributos usados | Clave de unión | Estado en el prototipo |
|---|---|---|---|---|
| Cassandra `fixture2030_comments.comentarios_por_partido` (Hito 6) | comentarios | `partido_id`, `creado_en`, `comentario_id`, `autor_id`, `estado_moderacion`, `reacciones` | `partido_id` + minuto (`creado_en` truncado) | **Implementado y medido** |
| IRIS `Fixture.Partido` / `Fixture.Evento` (Hito 9) | eventos del partido | `Codigo`, `Evento.Tipo`, `Evento.Minuto`, jugador | `Codigo = partido_id`; `Minuto` del partido ↔ minuto de reloj usando la hora de inicio | Diseño (los partidos de laboratorio P901-P904 no existen en IRIS) |
| InfluxDB `estadisticas_equipo` (Hito 8) | posesión, pases, tiros | `partido_id`, `equipo_id`, agregados por minuto (`date_bin`) | `partido_id` + minuto | Diseño |
| MongoDB `equipos` (Hito 4) | dimensión equipo | `_id`, `nombre`, `confederacion`, `grupo` | `equipo_id` | Diseño |

## Grano, medidas y modelo

**Grano**: una fila por **partido × minuto de reloj (UTC)**.

| Medida | Cálculo | Origen |
|---|---|---|
| `comentarios` | cantidad de `comentario_id` distintos en el minuto | Cassandra |
| `ocultos` | comentarios con `estado_moderacion != VISIBLE` | Cassandra |
| `reacciones` | suma de `reacciones` | Cassandra |
| `autores_distintos` | cantidad de `autor_id` distintos en el minuto | Cassandra |
| `eventos`, `goles`, `tarjetas` | conteo por tipo (diseño) | IRIS |
| `posesion_local_pct` | promedio del minuto (diseño) | InfluxDB |

**Procedencia por fila** (implementado): `fuente` (tabla de origen), `ventana_origen` (bucket de 5 min leído),
`filas_leidas` (filas de la ventana al momento del ETL), `etl_utc`, `version_etl`. Además `etl_marcas` guarda,
por partido y ventana, cuántas filas se leyeron y cuántos minutos se escribieron.

**Estructura** (prototipo en Cassandra, keyspace `fixture2030_mart`):

```sql
CREATE TABLE fixture2030_mart.actividad_partido_minuto (
  partido_id text, minuto timestamp,
  comentarios int, ocultos int, reacciones int, autores_distintos int,
  fuente text, ventana_origen timestamp, filas_leidas int, etl_utc timestamp, version_etl text,
  PRIMARY KEY ((partido_id), minuto));
```

Un partido ocupa una partición de ~120-200 filas: la serie completa se lee en una consulta. Para preguntas
entre partidos (por ejemplo, "los 10 minutos más activos del torneo") convendría además una copia en un
motor con SQL y `GROUP BY` (IRIS SQL o un almacén columnar), cargada desde esta misma proyección.

## Flujo de extracción, transformación y carga (RF13)

```
Cassandra (operacional) ──extracción por partición completa──▶ ETL (scripts/data_mart_etl.py)
   (partido, bucket, shard 0..7)                                  │ deduplica por comentario_id
                                                                  │ agrupa por minuto, cuenta, suma
                                                                  ▼
                                    fixture2030_mart.actividad_partido_minuto (upsert por clave)
                                    fixture2030_mart.etl_marcas (control por ventana)
```

| Aspecto | Decisión |
|---|---|
| Origen | Particiones completas `(partido, bucket_5m, shard)`; nunca escaneos ni `ALLOW FILTERING` |
| Transformación | Truncar `creado_en` al minuto; deduplicar por `comentario_id`; contar, sumar y distinguir autores |
| Frecuencia | Cada 5 minutos, procesando las ventanas **cerradas** (propuesta: tarea programada; en el prototipo se ejecuta a mano) |
| Retraso esperado | Ventana de 5 min + 2 min de tolerancia = un minuto llega al Data Mart entre 7 y 12 minutos después. Aceptable para análisis; **no** sirve para el feed en vivo (que sigue en el camino operacional) |
| Datos tardíos | Tolerancia (marca de agua) de 2 min; además, cada ejecución reprocesa las ventanas de las últimas horas (`--desde-horas`), así que un comentario tardío se incorpora en la ejecución siguiente |
| Duplicados | En la fuente: se cuenta cada `comentario_id` una sola vez. En el destino: upsert por `(partido_id, minuto)`; reprocesar reescribe la misma fila con el valor recalculado (idempotente, no suma dos veces) |
| Fallas parciales | Cada ventana es independiente y su resultado se recalcula completo: si el ETL se corta a mitad, la siguiente ejecución reprocesa todo el rango y converge. `etl_marcas` permite ver qué ventanas se procesaron y cuándo |
| Faltantes | Un minuto sin comentarios no genera fila (se interpreta como 0 al consultar). Si una fuente no responde, se reintenta en la ejecución siguiente; no se escribe un 0 que oculte la falla |

## Validación de conteos y agregados (medido)

`scripts/data_mart_etl.py validar` relee la fuente en las mismas ventanas que registró `etl_marcas` y compara
(`evidencia/data_mart/validacion.json`, ejecución del 2026-11-13 17:30 UTC):

| Partido | Ventanas | Comentarios en la fuente | Suma en el Data Mart | Minutos | Coincide |
|---|---|---|---|---|---|
| P901 | 49 | 132.000 | 132.000 | 228 | sí |
| P902 | 49 | 48.126 | 48.126 | 228 | sí |
| P903 | 49 | 36.354 | 36.354 | 228 | sí |
| P904 | 49 | 23.994 | 23.994 | 227 | sí |

La carga leyó 240.474 filas de 1.568 particiones en 1,22 s, descartó 0 duplicados y escribió 911 filas en
0,23 s (`evidencia/data_mart/etl_ultima_carga.json`). Los totales incluyen los 200.000 comentarios precargados y
los publicados por las corridas de carga.

## Diferencia entre consultar la fuente y consultar la proyección

| | Fuente operacional | Proyección analítica |
|---|---|---|
| Frescura | inmediata | 7-12 min de atraso |
| Costo por consulta | cientos de particiones, todas las filas | 1 partición, 1 fila por minuto |
| Impacto en el camino operacional | compite con el feed en vivo | ninguno al consultar (el ETL lee una vez cada 5 min) |
| Disponibilidad | depende de todas las fuentes que cruce | la proyección responde aunque una fuente esté caída (con el último dato cargado) |
| Costo | — | duplicación (911 filas para 240.474 comentarios), un proceso más que operar, consistencia eventual |
