# Cardinalidad y escalabilidad

## Variación de cada dimensión (torneo completo)

| Tag | Valores distintos | Tablas | Observación |
|---|---|---|---|
| partido_id | 104 | todas | crece con el calendario, acotado |
| equipo_id | 48 | 3 | fijo |
| jugador_id | 672 usados (48 x 14) de 1.248 convocados | rendimiento_jugador | acotado por la lista de buena fe |
| tipo_evento | 8 | eventos_partido | catálogo cerrado |
| plataforma | 3 | actividad_usuarios | catálogo cerrado |
| condicion | 2 | estadisticas_equipo | dependiente del partido + equipo |
| fase | 7 | 2 | dependiente del partido |
| sede_id | 23 | estadisticas_equipo | dependiente del partido |
| pais_sede | 6 | 2 | dependiente del partido |

`condicion`, `fase`, `sede_id` y `pais_sede` dependen funcionalmente de `partido_id`: no
multiplican la cantidad de series y permiten filtrar y comparar sin un JOIN (PA3, PA7).

## Estimación de series

| Tabla | Clave de serie | Fórmula | Series (104 partidos) |
|---|---|---|---|
| estadisticas_equipo | partido_id, equipo_id | 104 x 2 | 208 |
| rendimiento_jugador | partido_id, equipo_id, jugador_id | 104 x 2 x 14 | 2.912 |
| eventos_partido | partido_id, equipo_id, tipo_evento | ≤ 104 x 2 x 8 = 1.664 | 1.505 (medido) |
| actividad_usuarios | partido_id, plataforma | 104 x 3 | 312 |
| **Total** | | | **4.937** |

`validacion.py` mide las series reales por partido y las compara con el manifiesto (V2).

## Atributos excluidos de los tags

| Atributo | Dónde queda | Por qué no es tag |
|---|---|---|
| jugador_id en eventos | field Utf8 | Ningún patrón filtra eventos por jugador con prioridad. Como tag pasaría de 1.664 a ~23.000 series sin una consulta que lo justifique. Si aparece ese patrón, se resuelve en rendimiento_jugador o con un filtro sobre el field. |
| id de evento | no se guarda | Un id único por punto crea **una serie por punto** (140.000 series para 140.000 eventos). El timestamp en ms + la serie ya identifican el evento. |
| user_id / session_id | no se guarda (vive en Redis, Hito 7) | Millones de valores: millones de series. La actividad se agrega por plataforma. |
| minuto | field Int64 | Varía cada 60 s; como tag multiplicaría las series por ~100 y el tiempo ya está en `time`. |
| posesión, velocidad, latencia | fields Float64 | Medidas de variación continua: como tag cada valor distinto crearía una serie. |
| x, y, xg | fields Float64 | Valores continuos. |
| descripción / texto libre | no se guarda | Cardinalidad ilimitada; los comentarios viven en Cassandra (Hito 6). |

## Riesgos

- **Explosión de cardinalidad** si se agrega un tag de alta variación: se controla revisando cada tag nuevo contra un patrón de acceso y midiendo las series con `validacion.py`.
- **Columnas dispersas**: en `eventos_partido`, `xg` solo existe en tiros. En InfluxDB 3 (columnar) los NULL son baratos; no se crea una tabla por tipo de evento.
- **Límites de la edición Core**: cantidad de bases, tablas y columnas por tabla, y cantidad de archivos Parquet que puede leer una consulta. El modelo usa 2 bases, 8 tablas y menos de 20 columnas por tabla.

## Límites del laboratorio

| Aspecto | Laboratorio (notebook) | Proyección del torneo |
|---|---|---|
| Volumen | perfil `demo` (0,33 M) y `lab` (~2 M) cargados y validados | perfil `torneo` = 17,3 M puntos generados (~300 MB gz, ~2,6 GB de line protocol) |
| Calendario | comprimido: 4 partidos simultáneos cada 3 h | 104 partidos en 39 días |
| Nodos | 1 contenedor, object store en disco local | ver "Crecimiento" |
| Medición | ver `pruebas_y_evidencia.md` | — |

Los valores de throughput y latencia se registran solo a partir de una medición real (RF13); no se proyectan números que no se midieron.

## Relación con el objetivo de 10M+ puntos

- 17,3 M puntos / 104 partidos. El pico real es de 4 partidos simultáneos: 4 x (2 + 22 + 3) puntos/s ≈ **108 puntos/s** más los eventos. La carga en vivo es baja; el desafío es la **carga masiva histórica** (re-procesos, backfill) y el **volumen acumulado**.
- Para cargar 17,3 M puntos a un ritmo R medido, el tiempo es 17,3 M / R. Con la medición del laboratorio se completa esa cuenta en `pruebas_y_evidencia.md`.
- Los datos crudos del torneo caben en un nodo (cientos de MB en Parquet comprimido). La retención de 14 días acota lo que se mantiene a precisión original.

## Crecimiento y cambios futuros

- **Más fuentes** (tracking a 10–25 Hz, sensores de estadio): multiplica los puntos por segundo, no las series. Se mantiene el mismo modelo y se ajusta el lote y la concurrencia; si la frecuencia sube, el tracking crudo puede ir a una tabla propia con retención más corta (horas).
- **Distribuir carga**: separar ingesta de consultas (InfluxDB 3 Enterprise permite nodos de escritura y de consulta sobre el mismo object store), mover el object store a S3/compatible y agregar una cola (Kafka) delante de la ingesta para absorber picos y reintentos.
- **Consultas sobre todo el torneo**: usar la base histórica de 1 minuto (60 veces menos puntos) en lugar del vivo. En Core una consulta que lee demasiados archivos Parquet se rechaza; las consultas del repositorio acotan siempre partido y rango (RNF8).
- **Observabilidad posterior**: las métricas de la plataforma (actividad_usuarios) pueden alimentar Grafana o alertas sin cambiar el modelo; el Processing Engine de InfluxDB 3 puede correr el downsampling y alertas como triggers programados.
