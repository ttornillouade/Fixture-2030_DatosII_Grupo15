# Hipótesis, optimización, repetición y comparación (RF7-RF11, 5.5)

Tabla completa y gráficos: [evidencia/comparacion.md](evidencia/comparacion.md),
`evidencia/comparacion_latencias.png`, `comparacion_distribucion.png`, `comparacion_recursos.png`.
Todas las cifras son medianas de 3 corridas del **mismo escenario** (60 VU, 120 s sostenidos, mismos datos);
entre paréntesis, mínimo–máximo.

## 1. Cuello de botella observado

| Señal (línea base) | Valor | Lectura |
|---|---|---|
| CPU del proceso de la API | 90 % de un núcleo | Saturado: Python ejecuta el código de la app en un núcleo por proceso |
| CPU de Cassandra | ~100 % de 1 núcleo, de 6 disponibles en la VM | Trabaja, pero tiene margen |
| CPU del generador | 3 procesos a ~34 % | No es el límite (ya se había corregido) |
| Latencia dentro de la API (lectura) | p50 140 ms con carga vs 18 ms sin carga | La request espera turno **dentro** del proceso |
| Latencia por operación | feed vivo, historial y publicar ≈ 205 ms todas | No depende de qué se pide: es cola, no costo de la consulta |

**Hipótesis H1**: el límite es la CPU del único proceso de la API. Cada lectura del feed hace 8 consultas a
Cassandra (una por shard) y la API decodifica hasta 168 filas (8 × `LIMIT 21`), las ordena y serializa 20.
Ese trabajo en Python, repetido ~150 veces por segundo, llena un núcleo; las requests esperan en la cola del
proceso.

**Pruebas para relacionar la hipótesis con la evidencia**: si H1 es cierta, (a) reducir el trabajo de Python
por request debe bajar la latencia aunque Cassandra siga igual, y (b) dar más núcleos a la API (más procesos)
también debe mejorar, hasta que se sature otra cosa. Se probó cada palanca **por separado** y después juntas,
para no atribuir a una lo que hizo la otra.

## 2. Optimización 1: caché de la primera página en Redis

| | |
|---|---|
| Problema que ataca | H1, por (a): el 75 % de las requests pide la **misma** primera página (ventana actual de 4 partidos, P901 con el 55 %). Se recalcula la misma respuesta cientos de veces por segundo |
| Cambio | `GET .../comentarios` sin cursor busca primero `fixture2030:cache:comentarios:{partido}:{bucket}:{limit}` en Redis; si no está, lee Cassandra y guarda la página con `PX = 1000 ms`. Sin invalidación al publicar (ver trade-off). Si Redis falla o tarda >200 ms, se lee Cassandra |
| Archivos | `hito-10-api/app/adaptadores/cache_comentarios.py` (nuevo), `app/servicios.py`, `app/config.py` (`CACHE_COMENTARIOS_TTL_MS`, 0 = desactivada), `.env.example` |
| Commit | `5817539` |
| Costo / riesgo | Frescura: el feed puede mostrar hasta 1 s de atraso. Una dependencia más en el camino de lectura (mitigada: nunca hace fallar la request). Memoria en Redis (despreciable: pocas claves de ~10 KB). Al vencer el TTL, varias requests simultáneas pueden ir juntas a Cassandra (efecto estampida, acotado a 1 por segundo por clave) |
| Prueba | `bash scripts/ejecutar_prueba_optimizada.sh cache` (1 proceso, TTL 1000 ms) |

**Resultado medido**:

| | Línea base | Caché | Variación |
|---|---|---|---|
| Throughput | 163,4 req/s | 248,2 (225,7–256,5) | **+52 %** |
| p50 / p95 / p99 | 203 / 399 / 487 ms | 73 / 238 / 368 ms | −64 % / −40 % / −24 % |
| Lectura dentro de la API p50 / p95 | 140 / 303 ms | 13 / 102 ms | |
| CPU API | 90 % | 80 % | la API ya no es el único límite |
| CPU Cassandra | 102 % | 72 % | −29 % aun atendiendo un 52 % más de tráfico |
| Errores / integridad | 0 % / OK | 0 % / OK (10.339 escrituras verificadas) | |

La primera repetición (225,7 req/s, p95 305 ms) fue más lenta que las otras dos (248 y 256 req/s); se informa
el rango completo. **No se midió la tasa de aciertos** de la caché en estas corridas (la métrica se agregó en el
Hito 13); con 4 claves calientes y TTL de 1 s, se esperan del orden de 4 lecturas a Cassandra por segundo para
~180 lecturas de feed en vivo por segundo (estimación, no medición).

## 3. Optimización 2: varios procesos de la API (`--workers 3`)

| | |
|---|---|
| Problema que ataca | H1, por (b): un proceso de Python usa un núcleo; la máquina tiene 6 |
| Cambio | `uvicorn --workers 3` (variable `API_WORKERS` en `scripts/iniciar_api.sh`; `api_lab.py --workers`) |
| Archivos | `hito-10-api/scripts/iniciar_api.sh`, `hito-12-.../scripts/api_lab.py` |
| Costo / riesgo | Memoria ×2,5 (174 → 430 MB): cada proceso tiene sus propios pools hacia las 6 bases (3 veces más conexiones). Cada proceso abre sus conexiones con su primera request (arranque en frío, ver §5). Las métricas en memoria quedan por proceso (el Hito 13 usa el modo multiproceso de `prometheus_client`) |
| Prueba | `bash scripts/ejecutar_prueba_optimizada.sh workers` (3 procesos, sin caché) |

**Resultado medido**: 237,9 req/s (+46 %), p50 82 ms, p95 260 ms, p99 383 ms. Pero **la CPU de la API sube a
145 % y la de Cassandra a 147 %, y el equipo completo queda al 98 %**: la mejora sale de usar más CPU, no de
hacer menos trabajo, y en esta notebook ya no queda margen (el generador también compite por esos núcleos).
Aparecieron 2 errores `ReadError` del cliente en ~86.000 requests (0,004 %); las 10.304 escrituras se
verificaron completas y sin sobrantes.

## 4. Optimizaciones 1 + 2 (configuración final propuesta)

| | Línea base | Caché + 3 workers | Variación |
|---|---|---|---|
| Throughput | 163,4 req/s | **272,8** (267,5–273,7) | **+67 %** |
| p50 | 203 ms | **58** (54–58) | −72 % |
| p95 | 399 ms | **186** (172–197) | −53 % |
| p99 | 487 ms | **273** (250–317) | −44 % |
| Máxima | 835 ms | 5.168 (561–9.236) | **regresión** (ver §5) |
| Lectura dentro de la API p50 / p95 | 140 / 303 ms | 5 / 33 ms | |
| CPU API / Cassandra | 90 % / 102 % | 93 % / 69 % | |
| CPU total del equipo | 79 % | 89 % | |
| Memoria API | 174 MB | 397 MB | +128 % |
| Tasa de error | 0 % | 0,006 % en 1 de 3 corridas (2 `ReadError`) | |
| Integridad | OK | **1 escritura fantasma en r1** (ver §5) | |

Con la caché, los 3 procesos tienen poco trabajo cada uno (93 % sumando los tres) y Cassandra hace menos que
en la línea base. Dentro de la API, la lectura pasó de 140 ms a 5 ms de mediana: **el tiempo restante que ve el
cliente (58 ms) ya está mayormente fuera de la API** (generador, red local y la propia notebook al 89 %). Con
este hardware, la próxima mejora no se puede medir sin separar el generador de la máquina de la API.

## 5. Regresiones y problemas que aparecieron

1. **Arranque en frío por proceso → escritura fantasma (integridad).** En `optimizada_cache_workers_r1`, un
   `POST` del **calentamiento** tardó 10.370 ms dentro de la API (log) porque fue la primera request de ese
   proceso: abrió la sesión de Cassandra mientras otras requests esperaban el mismo lock. El cliente cortó a los
   10 s (`TIMEOUT_CLIENTE`), pero **Cassandra aplicó el batch**: `validar_integridad.py` encontró 3.841 filas de
   la corrida para 3.840 respuestas 201 (`sobrantes_vs_201 = 1`). No hay pérdida ni duplicado, pero un cliente
   que reintentara ese POST crearía un comentario duplicado. Se informa como **integridad no OK** en vez de
   descartar la corrida.
   - La conexión inicial además intenta primero `::1` (IPv6; en Windows `localhost` resuelve primero a IPv6 y
     los puertos están publicados solo en `127.0.0.1`) y deja un traceback en el log antes de conectar por IPv4.
   - **Correcciones propuestas (no implementadas ni medidas)**: abrir las sesiones de todas las bases al
     iniciar cada proceso (evento `startup` de FastAPI), usar `127.0.0.1` en lugar de `localhost` en `.env`, y
     hacer el POST idempotente con un id generado por el cliente (`Idempotency-Key` o `comentarioId` del
     cliente), para que un reintento no duplique.
2. **Pausas de ~5 s del lado del cliente.** En `optimizada_cache_workers_r1` (segundo 111 del sostenimiento,
   22 requests > 2 s) y `r2` (8 requests) hubo grupos de requests que tardaron ~5,3 s **para el cliente**,
   mientras el log de la API no registra ninguna request de más de 1 s en el sostenimiento. La espera ocurrió
   antes de que la API recibiera la request (cola de conexiones, scheduling de Windows con el equipo al
   89-98 % de CPU). Por eso la latencia **máxima** empeora aunque p50-p99 mejoren: es una limitación del
   laboratorio con todo en la misma máquina, no del diseño, pero no se puede descartar sin otra máquina para el
   generador.

## 6. Trade-offs documentados (RF11)

| Optimización | Ganancia | Costo |
|---|---|---|
| Caché Redis (TTL 1 s) | +52 % throughput con **menos** CPU de Cassandra | **Frescura**: hasta 1 s de atraso en el feed; un componente más en el camino de lectura; posible estampida al vencer el TTL. Se descartó invalidar al publicar: con ~27 publicaciones/s (≈15/s en P901), la clave caliente se borraría unas 15 veces por segundo y la caché casi no tendría aciertos |
| 3 workers | +46 % throughput sin cambiar código | **Memoria** ×2,5, 3 veces más conexiones a cada base, más CPU total (el equipo al 98 %), arranque en frío por proceso |
| Ambas | +67 % throughput, p95 −53 % | Suma de los anteriores; la latencia máxima empeoró por la saturación de la notebook |

## 7. Decisión del equipo

Se adopta **caché (TTL 1 s) + varios procesos** para el flujo de comentarios en vivo, con estas condiciones:

- la caché solo para la primera página (sin cursor) y con TTL corto: un atraso de 1 s es aceptable para un
  feed de hinchas, no lo sería para el estado del partido (IRIS) ni para sesiones;
- la cantidad de procesos se dimensiona por núcleos libres del servidor de la API (en producción, en un
  servidor separado de las bases y del generador);
- antes de pasar a producción, corregir el arranque en frío (abrir conexiones al iniciar cada proceso) y la
  idempotencia del POST (§5).

La API conserva por defecto el comportamiento del Hito 10 (`CACHE_COMENTARIOS_TTL_MS=0`, 1 proceso); la
configuración optimizada se activa por variables de entorno.

## 8. Repetición en las mismas condiciones (RF9, RNF3)

| Condición | Línea base | Optimizadas |
|---|---|---|
| Escenario | `config/escenario.json` | el mismo archivo, sin cambios |
| Datos precargados | 200.000 comentarios (`datos_preparados.json`) | los mismos (verificados en cada corrida: `precargados.coincide = true`) |
| Hardware y contenedores | misma PC, mismos contenedores y versiones | iguales; corridas consecutivas, sin otras tareas |
| Generador | 3 procesos | 3 procesos |
| Diferencias declaradas | — | (1) la ventana actual acumula los comentarios publicados por las corridas anteriores que cayeron en los mismos 5 minutos; no cambia el costo de lectura (`LIMIT 21` por shard); (2) el commit de la API (`f09df39` → `5817539`) cambia solo por la caché, que en la línea base no existía |
