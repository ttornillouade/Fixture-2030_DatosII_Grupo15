# Línea base (RF4, RF5, RF6, 5.4)

Todas las cifras de este documento son **mediciones reales** del laboratorio descrito en
`compose-o-instrucciones-del-entorno.md`, tomadas el 2026-11-13 entre las 16:50 y las 16:59 UTC.

## Qué se ejecutó

| | |
|---|---|
| Comando | `bash scripts/ejecutar_linea_base.sh` (3 repeticiones de `correr_escenario.sh linea_base_rN 1 0`) |
| Código | commit `f09df39`: API del Hito 10 **sin cambios** (sin caché, 1 proceso uvicorn) |
| Configuración de la API | `TIMEOUT_S=3`, 1 proceso uvicorn, pool de hilos por defecto de FastAPI (40), `--no-access-log` |
| Productos | Cassandra 5.0.9 (`cassandra:latest`, heap 1 GB), Redis `redis:latest` (AOF everysec, 256 MB), resto según `versiones` en cada `resumen.json` (imagen + digest) |
| Datos | 200.000 comentarios precargados (`evidencia/datos_preparados.json`) + los publicados por cada corrida |
| Escenario | `config/escenario.json`: 60 VU, 15 s calentamiento + 30 s rampa + **120 s sostenimiento**, 75/15/10 % |
| Evidencia | `evidencia/linea_base_r1_20261113T165018Z`, `..._r2_20261113T165324Z`, `..._r3_20261113T165628Z` (cada una con `resumen.json`, `requests.csv`, `recursos.csv`, `servidor.json`, `integridad.json`, `ids_creados.txt`) |

## Resultados (sostenimiento de 120 s, 60 VU)

| Métrica | r1 | r2 | r3 |
|---|---|---|---|
| Requests | 19.541 | 19.612 | 19.626 |
| **Throughput** | **162,8 req/s** | **163,4 req/s** | **163,6 req/s** |
| Exitosas / errores | 19.541 / 0 | 19.612 / 0 | 19.626 / 0 |
| Latencia mínima | 22 ms | 14 ms | 20 ms |
| Latencia media | 223 ms | 221 ms | 221 ms |
| **p50** | **206,6 ms** | **203,4 ms** | **203,4 ms** |
| p90 | 358 ms | 357 ms | 353 ms |
| **p95** | **399,5 ms** | **398,8 ms** | **390,8 ms** |
| **p99** | **485,7 ms** | **517,0 ms** | **487,2 ms** |
| Máxima | 744 ms | 920 ms | 835 ms |
| Lectura, latencia del servidor p50 / p95 | 140 / 301 ms | 139 / 303 ms | 141 / 307 ms |
| Escritura, latencia del servidor p50 / p95 | 160 / 322 ms | 162 / 340 ms | 160 / 337 ms |
| CPU API (% de 1 núcleo) | 90,5 | 89,4 | 90,6 |
| Memoria API | 174 MB | 173 MB | 176 MB |
| CPU Cassandra (contenedor) | 90 % | 102 % | 102 % |
| CPU Redis | 1 % | 1 % | 1 % |
| CPU del generador (3 procesos) | 103 % | 104 % | 101 % |
| CPU total del equipo | 79 % | 80 % | 79 % |
| Escrituras enviadas = 201 = verificadas en las 2 tablas | 2.401 | 2.324 | 2.439 |
| Integridad | OK | OK | OK |

Por operación (r1): feed en vivo 121,8 req/s (p50 205 ms, p95 396 ms); feed de historial 24,9 req/s
(p50 206 ms, p95 395 ms); publicar 16,2 req/s (p50 218 ms, p95 430 ms). Las tres operaciones tienen
casi la misma latencia: **el tiempo no depende de qué se pide, sino de esperar turno**.

**Estabilidad**: la variación entre repeticiones es menor al 1 % en throughput y al 2 % en p50 y p95.
El p99 y el máximo varían más (487-517 ms, 744-920 ms), como es esperable en la cola de la distribución.

## Cómo se separaron las mediciones (RF6)

| Capa | Qué se midió | Qué dice |
|---|---|---|
| Generador | latencia de cliente, CPU de sus 3 procesos (~34 % cada uno) | El generador **no** está saturado (ninguno de sus procesos llega a un núcleo) |
| API | duración en el log (servidor), CPU y memoria del proceso | El proceso está en ~90 % de un núcleo: **saturado** (Python ejecuta el código de la app en un núcleo por proceso) |
| Cassandra | CPU del contenedor (`docker stats`) | ~100 % de un núcleo de los 6 de la VM: trabaja, pero tiene margen |
| Redis | CPU del contenedor | ~1 %: no participa en este flujo en la línea base |
| Sistema operativo | CPU total | 79-80 % del equipo: hay margen, pero no mucho (todo corre en la misma máquina) |

**Diferencia cliente vs servidor**: p50 de ~205 ms en el cliente contra ~140 ms dentro de la API. Los
~65 ms restantes son tiempo **antes** de que la request llegue al middleware (cola del loop de uvicorn,
lectura del socket, parseo HTTP) más la red local y el propio generador. Sin carga, el mismo endpoint
responde en ~18 ms dentro de la API (exploración).

## Hallazgo previo: el generador era el cuello de botella

La primera corrida exploratoria usó **un solo proceso** generador
(`evidencia/exploracion_generador_1_proceso_20261113T163715Z`):

| | 1 proceso generador | 3 procesos generadores |
|---|---|---|
| Throughput | 78,8 req/s | 163,6 req/s |
| p50 cliente | 437 ms | 204 ms |
| p50 servidor (log de la API) | **18 ms** | 142 ms |
| CPU del generador | 93 % (1 núcleo) | ~102 % (3 procesos, ~34 % cada uno) |
| CPU de la API | 43 % | 91 % |

Con un proceso, el generador estaba al 93 % de un núcleo y la API respondía en 18 ms: la latencia de
437 ms la producía **el cliente**, no el sistema. Si se hubiera tomado esa corrida como línea base, se
habría "optimizado" la API para un problema que no tenía. Por eso el generador se reparte en 3 procesos y
cada corrida registra su CPU (nota 7 de la consigna: *el generador también puede ser el cuello de botella*).

## Corrida descartada

La primera ejecución de la línea base se descartó por interferencia (descarga de imágenes de Docker en
paralelo): ver `evidencia/descartada_interferencia_docker_pull_20261113T164633Z/LEEME.md`. Se conserva
porque mostró escrituras aplicadas cuyo cliente recibió un error.
