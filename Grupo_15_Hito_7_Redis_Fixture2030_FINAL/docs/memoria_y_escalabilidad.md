# Memoria y escalabilidad

## Política local

El contenedor se configura con:

```text
maxmemory 256mb
maxmemory-policy noeviction
```

## Por qué `noeviction`

La misma instancia del laboratorio contiene:

- sesiones activas;
- caché reconstruible;
- ranking temporal.

Una política LRU global podría expulsar una sesión todavía válida solamente porque un conjunto de claves de caché aumentó la presión de memoria.

Se prefiere `noeviction` para que la presión de memoria no transforme silenciosamente una sesión válida en una sesión ausente.

## Trade-off

Con `noeviction`, una operación que requiere más memoria puede fallar cuando se alcanza `maxmemory`.

Por eso el comportamiento esperado es:

- caché: ante fallo de escritura, continuar desde la fuente de verdad sin cachear;
- sesión: registrar error y no asumir que la renovación/creación fue exitosa;
- monitoreo: observar `used_memory`, `evicted_keys`, errores y tasa de crecimiento.

## TTL vs evicción

Son mecanismos distintos.

**TTL** responde a validez temporal:

```text
sesión inactiva -> vence
cache antigua -> vence
ranking diario -> vence
```

**Evicción** responde a presión de memoria.

En nuestro laboratorio `noeviction` significa que Redis no elige claves para eliminar cuando alcanza el límite; las expiraciones por TTL siguen funcionando normalmente.

## Producción

No presentamos este nodo único como arquitectura de alta disponibilidad.

Una evolución razonable sería separar cargas:

```text
Redis de sesiones
  -> política conservadora / replicación / Sentinel o Cluster

Redis de caché
  -> política de evicción orientada a caché
```

También podrían separarse límites de memoria, métricas y objetivos de disponibilidad.

La elección concreta dependería del volumen y del SLA real.
