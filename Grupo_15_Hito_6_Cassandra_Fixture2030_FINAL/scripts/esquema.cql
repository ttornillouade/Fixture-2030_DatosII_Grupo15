CREATE KEYSPACE IF NOT EXISTS fixture2030_comments
WITH replication = {'class':'NetworkTopologyStrategy','datacenter1':1}
AND durable_writes = true;

USE fixture2030_comments;

CREATE TABLE IF NOT EXISTS comentarios_por_partido (
    partido_id text,
    bucket_5m timestamp,
    shard tinyint,
    creado_en timestamp,
    comentario_id text,
    autor_id text,
    contenido text,
    estado_moderacion text,
    reacciones int,
    PRIMARY KEY ((partido_id, bucket_5m, shard), creado_en, comentario_id)
) WITH CLUSTERING ORDER BY (creado_en DESC, comentario_id DESC);

CREATE TABLE IF NOT EXISTS comentarios_por_usuario (
    autor_id text,
    dia_bucket date,
    creado_en timestamp,
    comentario_id text,
    partido_id text,
    bucket_5m timestamp,
    shard tinyint,
    contenido text,
    estado_moderacion text,
    reacciones int,
    PRIMARY KEY ((autor_id, dia_bucket), creado_en, comentario_id)
) WITH CLUSTERING ORDER BY (creado_en DESC, comentario_id DESC);
