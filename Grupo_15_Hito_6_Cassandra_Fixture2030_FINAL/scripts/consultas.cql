CONSISTENCY ONE;
USE fixture2030_comments;

// Feed de una partición física del partido.
SELECT creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones
FROM comentarios_por_partido
WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:00:00+0000' AND shard=0
LIMIT 20;

// Ventana temporal dentro de la misma partición.
SELECT creado_en,comentario_id,autor_id,contenido
FROM comentarios_por_partido
WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:00:00+0000' AND shard=0
  AND creado_en >= '2030-06-08 20:00:00+0000'
  AND creado_en <  '2030-06-08 20:05:00+0000'
LIMIT 20;

// Historial de usuario sin ALLOW FILTERING.
SELECT creado_en,comentario_id,partido_id,contenido,estado_moderacion,reacciones
FROM comentarios_por_usuario
WHERE autor_id='U0001' AND dia_bucket='2030-06-08'
LIMIT 20;
