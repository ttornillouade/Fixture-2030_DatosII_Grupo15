# Datos de prueba del Hito 12

Todos los datos son **sintéticos y generados por el equipo** (RNF7). No hay datos personales: los
"usuarios" son códigos `U9xxxxx` y los textos son frases fijas de fútbol.

## Qué se genera

| Conjunto | Generador | Cantidad | Dónde queda |
|---|---|---|---|
| Historial de comentarios | `scripts/preparar_datos.py` | 200.000 comentarios (400.000 filas: tabla por partido + tabla por usuario) | Cassandra, keyspace `fixture2030_comments` (el del Hito 6) |
| Comentarios publicados durante la prueba | `scripts/ejecutar_carga.py` (vía `POST` de la API) | ~10 % de las requests (~2.400 por corrida de 120 s) | mismas tablas |
| Proyección analítica | `scripts/data_mart_etl.py` | 1 fila por partido y minuto | keyspace `fixture2030_mart` |

## Decisiones de generación

- **Partidos de laboratorio P901-P904**: el fixture real del Hito 5 llega a P128. Usar códigos propios
  permite borrar exactamente lo que se cargó sin tocar los datos de los otros hitos (RNF11).
- **Distribución desigual entre partidos**: P901 55 %, P902 20 %, P903 15 %, P904 10 %. Representa un
  partido "caliente" (por ejemplo, un clásico) con otros en paralelo. El generador de carga usa la misma
  proporción, así que P901 es la **clave caliente** del escenario.
- **Ventanas de 5 minutos de las últimas 3 horas** (36 ventanas), con más comentarios en las ventanas
  recientes (rampa lineal: un partido que se va calentando). La ventana más cargada tiene ~6.000
  comentarios de P901 (≈750 por shard).
- **Shard = crc32(comentarioId) % 8**, igual que la API, para que las particiones tengan el mismo tamaño
  que tendrían con datos reales.
- **10.000 usuarios** (`U900000`-`U909999`), elegidos al azar: no hay usuario caliente.
- **Moderación**: 2 % `OCULTO`; **reacciones** con distribución de Pareto (pocos comentarios concentran
  muchas reacciones).
- **Semilla fija (2030)** e ids deterministas (`L-<partido>-<n>`): repetir la carga reescribe las mismas
  filas (upsert de Cassandra). No duplica.

Como las ventanas se calculan respecto de la hora de ejecución, los timestamps cambian entre ejecuciones;
la distribución y la cantidad, no. `docs/evidencia/datos_preparados.json` registra la ventana exacta de la
carga usada en las mediciones, los conteos por partido y por ventana, y el tiempo de carga.

## Volumen probado vs volumen proyectado

| | Laboratorio (medido) | Proyección del TPO (Hito 6) |
|---|---|---|
| Comentarios almacenados | 200.000 precargados + ~2.400 por corrida | ~1,1 M en la carga de volumen del Hito 6; millones por partido de alta audiencia en el torneo |
| Partidos con actividad simultánea | 4 | varios partidos en simultáneo (por ejemplo, la última fecha de grupos) |
| Lecturas del feed | ~150 lecturas/s | decenas de miles por segundo en un pico (estimación, no medida) |

**Por qué el volumen almacenado afecta poco a este flujo**: cada lectura de página pide `LIMIT 21` a cada
uno de los 8 shards de **una** ventana de 5 minutos. El costo depende del tamaño de la página y de la
cantidad de shards, no del total de comentarios del partido: es una lectura acotada por diseño (Hito 6).
Lo que sí crece con el torneo es la **tasa de requests**, y eso es lo que se estresa en este hito. La
extrapolación a producción está en `docs/integridad_y_limitaciones.md` y no se presenta como medición.

## Validación de la carga

`preparar_datos.py` informa las filas escritas y los errores (0 en la carga usada). `validar_integridad.py`
vuelve a contar, después de cada prueba, los comentarios `L-*` por partido y los compara con el manifiesto
(`precargados.coincide`).
