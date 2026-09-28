# Decisiones de particionamiento y trade-offs

## Por qué no `partido_id` solo
Concentraría todos los comentarios de un partido popular en una partición y token lógico.

## Bucket de 5 minutos + 8 shards
Supuesto de diseño:

```text
pico global = 8.000 comentarios/s
60% en un partido = 4.800 comentarios/s
bucket = 300 s
shards = 8
```

Estimación extrema por partición:

```text
4.800 * 300 / 8 = 180.000 filas
```

El objetivo del grupo es mantener el orden de magnitud por debajo de ~200.000 filas por partición bajo ese supuesto. No se presenta como límite universal de Cassandra.

## Trade-off

```text
menos hotspot de escritura
         ↕
más fan-out de lectura
```

El feed debe consultar 8 shards y fusionarlos. Se acepta porque el problema prioritario es la concurrencia masiva sobre pocos partidos populares.

## Duplicación por usuario
La tabla secundaria mejora una consulta distinta a costa de doble escritura y de mantener coherencia en updates/deletes.

## TTL
No se aplica TTL automático: no hay requisito funcional de expiración y TTL/DELETE producen tombstones. Si luego se necesita un feed efímero, conviene una estructura derivada con retención específica.
