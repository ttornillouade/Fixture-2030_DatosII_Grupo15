# Rendimiento — ejecución real

## Método

La prueba se ejecutó el **27/09/2026 a las 23:43:01 (-03)** sobre el contenedor local `fixture2030-redis`. Se realizaron **50.000 operaciones por prueba** con **50 clientes concurrentes**, utilizando `redis-benchmark` dentro del contenedor.

Las operaciones medidas fueron `SET` con TTL de 300 segundos, `GET` y `HSET` sobre una sesión de prueba. Las claves de benchmark pertenecen al namespace `fixture2030:bench:*` y no representan datos funcionales del Fixture.

## Ambiente observado

```text
Redis:                  8.10.2
Allocator:              jemalloc 5.3.0
Arquitectura:           64 bits
Contenedor:             fixture2030-redis
CPU observada:          0.27 %
Memoria Docker:         7.652 MiB / 7.75 GiB
maxmemory Redis:        256 MiB
maxmemory-policy:       noeviction
```

`docker stats` e `INFO memory` utilizan criterios de medición distintos y fueron tomados en momentos diferentes; por eso sus cifras de memoria se registran por separado y no se interpretan como equivalentes directos.

## Resultados

| Operación | Throughput observado | p50 |
|---|---:|---:|
| `SET ... EX 300` | 118.764,84 req/s | 0,335 ms |
| `GET` | 149.253,73 req/s | 0,175 ms |
| `HSET` sesión | 105.708,25 req/s | 0,359 ms |

En esta ejecución local, `GET` presentó la mayor tasa y la menor mediana de latencia. `HSET` fue la operación con menor throughput de las tres medidas, aunque superó las 100.000 solicitudes por segundo en este entorno.

Estos valores describen únicamente la prueba local y no se extrapolan a producción.

## Memoria observada desde Redis

```text
used_memory:          11.80 MiB
used_memory_peak:     12.66 MiB
used_memory_dataset:  5.63 MiB aprox.
maxmemory:            256 MiB
policy:               noeviction
fragmentation_ratio:  2.94
```

La prueba permaneció ampliamente por debajo del límite configurado de 256 MiB, por lo que no se observó presión de memoria ni fue necesario aplicar la política `noeviction`.

## Interpretación y limitaciones

La medición valida el comportamiento de las operaciones principales en el laboratorio local, pero no demuestra capacidad productiva para millones de usuarios. El entorno tiene un único nodo Redis, comunicación local por Docker, datos sintéticos y ausencia de latencia de red productiva.

La prueba registra `p50`, pero no caracteriza p95/p99. Tampoco mide failover, réplicas, Sentinel, Redis Cluster, red multirregional, concurrencia combinada entre sesiones/caché/ranking ni el comportamiento al alcanzar efectivamente `maxmemory`.

La prueba funcional con `ZINCRBY` se mantiene separada porque su objetivo es demostrar atomicidad y ausencia de incrementos perdidos, no solo throughput.

## Evidencia

Salida completa:

```text
docs/evidencia/rendimiento_hito7_20260927_234301.txt
```
