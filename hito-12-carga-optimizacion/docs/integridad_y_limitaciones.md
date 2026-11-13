# Integridad y limitaciones (RF15, RNF4, RNF6, RNF14, 5.8)

## Cómo se valida la integridad

`scripts/validar_integridad.py` corre después de **cada** corrida (lo llama `correr_escenario.sh`) y deja
`integridad.json` junto a los resultados. No asume que un 2xx significa dato correcto:

| Verificación | Cómo | Qué detecta |
|---|---|---|
| Cada 201 está escrito | Lectura puntual por clave completa en `comentarios_por_partido` y en `comentarios_por_usuario` | Escrituras perdidas, batch aplicado a medias |
| Contenido correcto | Texto y autor iguales a los que devolvió la API | Datos alterados |
| Sin fantasmas | Filas de la corrida (texto `carga <etiqueta> ...`) en todas las particiones tocadas = cantidad de 201 | Escrituras aplicadas cuya respuesta no llegó al cliente |
| Ids únicos | `comentarioId` repetidos entre los 201 | Duplicados |
| Datos previos intactos | Conteo de comentarios `L-*` por partido = manifiesto de la preparación | La prueba no alteró los datos existentes |
| Caché coherente | Pasado el TTL, la primera página de la API = la armada leyendo Cassandra | La caché sirve datos distintos a la fuente |

## Resultados

| Configuración | Corridas | Escrituras con 201 | Faltan | Contenido distinto | Fantasmas | Duplicados | Precargados intactos | Caché = fuente |
|---|---|---|---|---|---|---|---|---|
| Línea base | 3 | 7.164 | 0 | 0 | 0 | 0 | sí | n/a |
| Caché | 3 | 10.339 | 0 | 0 | 0 | 0 | sí | sí (4/4 partidos) |
| 3 workers | 3 | 10.304 | 0 | 0 | 0 | 0 | sí | n/a |
| Caché + 3 workers | 3 | 11.485 | 0 | 0 | **1** (r1) | 0 | sí | sí |
| Corrida descartada (interferencia) | 1 | 583 | 0 | 0 | **10** | 0 | sí | n/a |

Rechazos: en las 12 corridas válidas (390.686 requests contando calentamiento y rampa) fallaron 5 del lado del
cliente, todas con 3 workers: 2 lecturas con `ReadError` y 3 publicaciones (2 `ReadError`, 1 timeout del
cliente). De esas 3 publicaciones, 2 no dejaron dato escrito y **1 sí** (el timeout del calentamiento de
`optimizada_cache_workers_r1`, el fantasma explicado en `hipotesis_y_optimizacion.md` §5). La API no devolvió
ningún 5xx en las corridas válidas. Los fantasmas son la consecuencia de que el `POST` no sea idempotente: el
servidor puede aplicar la escritura después de que el cliente dejó de esperar. Corrección propuesta: clave de
idempotencia generada por el cliente.

## Volumen probado vs capacidad proyectada (RNF6)

| | Medido en el laboratorio | Proyección (no medida) |
|---|---|---|
| Concurrencia | 60 usuarios virtuales con pausas de 50-250 ms | cientos de miles de hinchas con la app abierta en un partido de alta audiencia |
| Throughput | 163 req/s (línea base) → 273 req/s (optimizado) en **una** PC de 6 núcleos que además corre el generador y las 6 bases | requiere varias instancias de la API detrás de un balanceador y Cassandra con varios nodos |
| Datos | 200.000 comentarios precargados + ~40.000 publicados | ~1,1 M (Hito 6) y más en el torneo; el costo de lectura del feed no depende del total (lectura acotada por ventana y `LIMIT`) |

**Extrapolación (estimación, no resultado)**: con la configuración optimizada, la lectura cuesta ~5 ms de
mediana dentro de la API. Si el costo fuera lineal, un núcleo atendería del orden de 100-200 lecturas por segundo
con caché; atender decenas de miles por segundo requeriría del orden de cientos de núcleos de API o, mejor,
servir la primera página desde una CDN/caché de borde con el mismo TTL de 1 s. Esto es un razonamiento de
orden de magnitud para dimensionar, **no una medición**: no se probó con más de una máquina.

## Limitaciones del entorno

1. **Todo en la misma máquina**: generador, API y bases compiten por 6 núcleos. Con la configuración final el
   equipo quedó al 89-98 % de CPU; parte de la latencia que ve el cliente (y las pausas de ~5 s) ocurre fuera
   de la API. No se puede separar del todo sin otra máquina.
2. **Un nodo por base** (RF=1 en Cassandra, Redis sin réplica): no se midió replicación, consistencia
   `QUORUM`, ni la caída de un nodo con la base en servicio.
3. **Windows + Docker Desktop**: los puertos pasan por la VM de WSL 2; `localhost` resuelve primero a IPv6 y
   los drivers reintentan por IPv4 (~2 s la primera vez). Los números en Linux nativo serían otros.
4. **Duración**: 120 s sostenidos por corrida. No se midió el comportamiento de horas (compactación de
   Cassandra, crecimiento de memoria).
5. **Tasa de aciertos de la caché**: no medida en estas corridas (se agregó como métrica en el Hito 13).
6. **CPU por contenedor** con `docker stats` cada 2 s: es una muestra, no un perfil; `docker stats` en sí
   consume algo de CPU.
7. **Alternativa relacional**: solo análisis conceptual (ver `comparacion_relacional.md`).

## Qué no puede generalizarse

- Que la caché mejore un 52 %: depende de cuántas requests piden la misma página (aquí, 4 claves calientes).
  Con muchos partidos poco vistos, la tasa de aciertos bajaría.
- Que 3 workers mejoren un 46 %: depende de que haya núcleos libres; en esta PC no quedaban.
- Que el cuello de botella sea la API: en un cluster con la API escalada horizontalmente, el próximo límite
  podría ser Cassandra (8 consultas por lectura sin caché).
