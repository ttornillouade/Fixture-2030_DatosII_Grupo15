# Modelo multidimensional

## Conceptos en InfluxDB 3

| Concepto | Significado en este módulo |
|---|---|
| Base de datos | `fixture2030_vivo` (14 días, precisión original) y `fixture2030_historico` (sin vencimiento, resúmenes de 1 min). |
| Tabla | Un fenómeno observado (antes "measurement"). |
| Tag | Dimensión indexada, de tipo `Dictionary(Int32, Utf8)`. Forma parte de la identidad de la serie y de la clave de ordenamiento. |
| Field | Valor observado, con tipo fijo (`Int64`, `Float64`, `Boolean`, `Utf8`). |
| Timestamp | Columna `time`, `Timestamp(Nanosecond)`. Se escribe con `precision=millisecond`. |
| Serie | Tabla + combinación de valores de tags. Dos puntos con la misma serie y el mismo timestamp se sobrescriben. |

## Tablas

### estadisticas_equipo — PA1, PA2, PA3

| Columna | Rol | Tipo | Semántica | Agregación correcta |
|---|---|---|---|---|
| partido_id | tag | string | P001..P104 (identidad del Hito 5) | filtro |
| equipo_id | tag | string | E001..E048 (Hito 4) | filtro / comparación |
| condicion | tag | string | local / visitante | comparación |
| fase | tag | string | grupos ... final | segmentación |
| sede_id, pais_sede | tag | string | sede del partido | segmentación |
| minuto | field | Int64 | minuto de juego (contexto) | last |
| posesion_pct | field | Float64 | % de posesión acumulado del partido | avg del bloque / last |
| pases_intentados, pases_completados, tiros, tiros_al_arco, recuperaciones, faltas, corners, goles | field | Int64 | contadores acumulados desde el inicio | max (= último) y diferencia entre bloques |
| xg_acum | field | Float64 | goles esperados acumulados | max / last |
| time | timestamp | ms | momento de la medición en el proveedor | — |

Serie = (partido_id, equipo_id); el resto de los tags dependen funcionalmente del partido y no multiplican series.

### rendimiento_jugador — PA4

| Columna | Rol | Tipo | Semántica | Agregación correcta |
|---|---|---|---|---|
| partido_id, equipo_id, jugador_id | tag | string | jugador = `E001J09` | filtro |
| minuto | field | Int64 | minuto de juego | last |
| velocidad_kmh | field | Float64 | muestra instantánea (gauge) | avg, max, percentiles |
| distancia_m | field | Float64 | distancia acumulada en el partido | max / last; diferencia por intervalo |
| sprints | field | Int64 | sprints acumulados (>25 km/h) | max / last |

Serie = (partido_id, equipo_id, jugador_id).

### eventos_partido — PA5

| Columna | Rol | Tipo | Semántica | Agregación correcta |
|---|---|---|---|---|
| partido_id, equipo_id | tag | string | | filtro |
| tipo_evento | tag | string | 8 valores: pase, tiro, gol, recuperacion, falta, tarjeta, corner, sustitucion | segmentación |
| jugador_id | **field** | Utf8 | autor del evento | se devuelve, no se indexa |
| minuto | field | Int64 | minuto de juego | — |
| exitoso | field | Boolean | pase completado / tiro al arco | count de verdaderos |
| x, y | field | Float64 | posición en la cancha | avg / mapas de calor |
| xg | field | Float64 | probabilidad de gol (solo tiros) | sum |
| valor | field | Int64 | siempre 1 | sum = count |

Serie = (partido_id, equipo_id, tipo_evento). Timestamp con milisegundos para ordenar eventos del mismo segundo.

### actividad_usuarios — PA6, PA7

| Columna | Rol | Tipo | Semántica | Agregación correcta |
|---|---|---|---|---|
| partido_id, plataforma, fase, pais_sede | tag | string | plataforma = web / ios / android | filtro / comparación |
| usuarios_activos | field | Int64 | gauge (sesiones activas en ese segundo) | avg, max; se puede sumar entre plataformas en el mismo instante, nunca en el tiempo |
| solicitudes, errores | field | Int64 | delta del último segundo | sum |
| latencia_p95_ms | field | Float64 | percentil 95 ya calculado por el backend | max (promediar percentiles no da un percentil) |

Serie = (partido_id, plataforma).

## Tablas resumidas (base histórica)

`estadisticas_equipo_1m`, `rendimiento_jugador_1m`, `eventos_partido_1m`, `actividad_usuarios_1m`: mismos tags, timestamp al inicio del minuto y fields agregados (ver `retencion_y_granularidad.md`).

## Precisión temporal (RF6)

- Captura: el proveedor envía con milisegundos y los eventos necesitan orden dentro del mismo segundo → **se almacena en ms**.
- Consulta: las estadísticas se leen por segundo (vivo) o por minuto (histórico).
- Se declara en `influx_comun.PRECISION_LP = "millisecond"`, en el manifiesto de cada generación y en cada request (`precision=millisecond`).
- Una precisión menor (segundos) haría colisionar eventos del mismo segundo en la misma serie y se sobrescribirían.

## Tipos consistentes (RNF6)

- Enteros siempre con sufijo `i` en el line protocol; floats siempre con punto decimal (`50.00`), aunque el valor sea entero.
- El primer punto fija el tipo de la columna. Un punto con otro tipo es rechazado (lo muestra `carga_lotes.py --demo-errores`).
- `validacion.py` (V5) compara los tipos de `information_schema.columns` con los declarados.
