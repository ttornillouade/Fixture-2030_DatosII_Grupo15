# Modelo clave/valor

## Convención de namespace

Todas las claves del módulo comienzan con:

```text
fixture2030:
```

Esto permite identificar dominio y propósito sin conocimiento implícito.

## Sesiones

```text
fixture2030:session:{session_id}
```

Tipo:

```text
HASH
```

Campos:

```text
session_id
user_id
created_at
last_activity
access_status
locale
```

TTL de producción:

```text
1800 segundos
```

El `session_id` real debería generarse con suficiente entropía. Los IDs incluidos en los scripts son únicamente de demostración.

## Caché de equipo

```text
fixture2030:cache:equipo:{equipo_id}
```

Tipo:

```text
HASH
```

TTL:

```text
300 segundos
```

Campos cacheados:

```text
id
nombre
pais
confederacion
grupo
```

La ficha es una copia reconstruible. La fuente de verdad continúa siendo el módulo MongoDB de Equipos del Hito 4.

## Ranking temporal

```text
fixture2030:ranking:partidos:consultas:{fecha}
```

Tipo:

```text
SORTED SET
```

- member: `partido_id`
- score: cantidad de consultas/actividad temporal
- actualización: `ZINCRBY`
- recuperación: `ZREVRANGE ... WITHSCORES`
- TTL: 172800 segundos (48 h)

`ZINCRBY` es un comando atómico de Redis, por lo que dos clientes concurrentes no realizan el clásico read-modify-write de manera separada.

## Metadatos del laboratorio

```text
fixture2030:meta:hito
```

Tipo `HASH`. Conserva parámetros documentales de la muestra y no representa información de negocio.
