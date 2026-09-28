# Modelo tabular

## Keyspace
`NetworkTopologyStrategy` con `datacenter1:1` porque el laboratorio tiene un único nodo. No se presenta como topología productiva.

## Tabla principal
`comentarios_por_partido`

```text
Partition key: (partido_id, bucket_5m, shard)
Clustering:    creado_en DESC, comentario_id DESC
```

- `partido_id`: contexto deportivo.
- `bucket_5m`: limita crecimiento temporal.
- `shard`: distribuye escrituras simultáneas.
- `creado_en`: orden natural del feed.
- `comentario_id`: desempata instantes iguales.

## Tabla secundaria
`comentarios_por_usuario`

```text
Partition key: (autor_id, dia_bucket)
Clustering:    creado_en DESC, comentario_id DESC
```

Resuelve una consulta distinta mediante duplicación controlada.

## Datos del comentario
ID, partido, autor, instante, contenido, estado de moderación y `reacciones`. Esta última es una métrica propia del comentario; no se usa para particionar ni para consultas globales.
