# Flujo seleccionado y escenario de carga (RF1, RF2, 5.1, 5.2)

## Flujo: comentarios en vivo durante un partido

**Situación del Fixture**: *actividad durante un partido* (5.2). Mientras se juega, miles de hinchas
tienen abierta la pantalla del partido: la app refresca el feed de comentarios cada pocos segundos y una
parte de ellos publica. Es el flujo de mayor tráfico de la plataforma y el que tiene picos más bruscos
(un gol multiplica la actividad).

| Aspecto | Definición |
|---|---|
| Quién genera la operación | La app del hincha (cliente móvil/web) a través de la API REST del Hito 10 |
| Endpoints | `GET /partidos/{codigo}/comentarios?bucket=&limit=20` (feed) y `POST /partidos/{codigo}/comentarios` (publicar) |
| Fuentes | **Cassandra** (`fixture2030_comments`, tablas `comentarios_por_partido` y `comentarios_por_usuario`, Hito 6). Después de la optimización, **Redis** como caché de lectura |
| Tipo de operación | Lectura (90 %) y escritura (10 %) |
| Datos que recibe | Feed: código de partido, ventana de 5 min (`bucket`), tamaño de página y cursor opcional. Publicar: `usuarioId` y `texto` (1-500 caracteres) |
| Qué hace | Feed: 8 consultas en paralelo (una por shard de la ventana, `LIMIT 21`), fusión por fecha descendente en la API y página de 20 con cursor. Publicar: `BATCH LOGGED` en las dos tablas |
| Respuesta esperada | Feed: `200` con hasta 20 comentarios ordenados y `nextCursor`. Publicar: `201` con el comentario creado (id y fecha del servidor) |
| Criterio de éxito | Código 2xx **y**, para las escrituras, que el comentario exista una sola vez en las dos tablas (`validar_integridad.py`). Un 2xx solo no alcanza (RF15) |
| Errores a registrar | `503 DEPENDENCY_UNAVAILABLE` (Cassandra rechaza la conexión), `504 DEPENDENCY_TIMEOUT` (no responde en 3 s), `400` (contrato), timeouts del cliente (10 s) y errores de conexión |
| Volumen y frecuencia proyectados | En el torneo, decenas de miles de lecturas por segundo en un partido de alta audiencia (estimación de diseño, no medida). En el laboratorio se prueban ~160-500 req/s |

**Por qué este flujo**: (1) es el de mayor volumen y concurrencia del TPO; (2) combina lectura y
escritura sobre la misma partición caliente (la ventana actual del partido más visto); (3) su diseño en
Cassandra tiene un costo de lectura conocido (8 consultas + fusión) que vale la pena medir; (4) permite
validar integridad de forma estricta (cada escritura tiene id único).

## Escenario de carga (`config/escenario.json`)

| Parámetro | Valor | Motivo |
|---|---|---|
| Datos iniciales | 200.000 comentarios precargados en P901-P904 (ver `datos-o-generadores/README.md`) | Particiones con el tamaño de un partido real |
| Modelo de carga | **Cerrado**: usuarios virtuales (VU) que repiten request → pausa | Representa usuarios con la app abierta; la tasa resultante es lo que se mide |
| Usuarios virtuales | 5 en calentamiento, **60** en sostenimiento | 60 VU saturan un proceso de la API en esta notebook (exploración) sin agotar la máquina |
| Pausa entre requests (think time) | 50-250 ms al azar (uniforme) | Refresco agresivo de la app; tasa objetivo ~400 req/s si la API no se demorara |
| Proporción de operaciones | 75 % feed de la ventana actual, 15 % feed de una ventana anterior, 10 % publicar | Lecturas dominantes; la mayoría sobre la ventana en vivo |
| Distribución de partidos | P901 55 %, P902 20 %, P903 15 %, P904 10 % | Un partido caliente (clave caliente) y otros en paralelo |
| Calentamiento | 15 s (no se mide) | Abrir conexiones y pools, cargar el código |
| Rampa | 30 s, lineal de 5 a 60 VU | Ver el comportamiento mientras crece la concurrencia |
| Sostenimiento | **120 s** (lo único que entra en las métricas) | Suficiente para ~20.000 requests y percentiles estables |
| Generador | 3 procesos de Python (asyncio + httpx), 20 VU cada uno | Con 1 proceso el generador era el cuello de botella (ver `linea_base.md`) |
| Timeout del cliente | 10 s | Mayor que el `TIMEOUT_S` de la API (3 s): si la API responde 504, se registra el 504 y no un timeout del cliente |
| Interrupción segura | Ctrl+C (guarda lo medido) o corte automático si >20 de las últimas 100 requests de un proceso fallan | Evita seguir castigando un sistema caído (RNF9) |
| Repeticiones | 3 por configuración | Ver variación entre corridas |
| Limpieza / reutilización | Los comentarios publicados quedan (cada corrida usa un texto único `carga <etiqueta> ...`); `limpiar_datos_de_prueba.py --confirmar` borra todo lo de P901-P904 | RNF11 |

### Comportamiento ante error

- Una respuesta 4xx/5xx o un timeout se registra con su tipo (`errores_por_tipo` en `resumen.json`) y el
  VU sigue con la próxima operación después de su pausa. **No hay reintentos**: reintentar un `POST` que
  no es idempotente podría duplicar comentarios, y se quiere ver el error tal cual.
- La validación posterior detecta escrituras que la base aplicó aunque el cliente no recibió el 201 (ver
  la corrida descartada en `evidencia/`).

### Cómo se mide

| Métrica | Método | Unidad |
|---|---|---|
| Latencia (cliente) | `perf_counter` alrededor de cada request en el generador: tiempo de respuesta HTTP completo | ms; mín, media, p50, p90, p95, p99, máx |
| Latencia (servidor) | Duración que la API registra en su log por request (middleware). `analizar_log_api.py` → `servidor.json` | ms (resolución 1 ms) |
| Throughput | Requests completadas en el sostenimiento / 120 s | req/s |
| Éxito / error | Por código HTTP y tipo de error, por operación | cantidad y % |
| Recursos | Cada 2 s: CPU del generador y de la API (`psutil`, por proceso), CPU/memoria de cada contenedor (`docker stats`), CPU/memoria total del SO | % de un núcleo (100 = 1 núcleo); MB |
| Integridad | `validar_integridad.py` (ver `integridad_y_limitaciones.md`) | conteos |

Todo queda asociado a fecha, commit, escenario, versiones de las imágenes y entorno en `resumen.json` (RNF2).
