CONSISTENCY ONE;
USE fixture2030_comments;

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones)
VALUES ('P001','2030-06-08 20:10:00+0000',3,'2030-06-08 20:12:15+0000','C-DEMO-001','U9999','Comentario temporal para CRUD','VISIBLE',0);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones)
VALUES ('U9999','2030-06-08','2030-06-08 20:12:15+0000','C-DEMO-001','P001','2030-06-08 20:10:00+0000',3,'Comentario temporal para CRUD','VISIBLE',0);

SELECT * FROM comentarios_por_partido WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:10:00+0000' AND shard=3 AND creado_en='2030-06-08 20:12:15+0000' AND comentario_id='C-DEMO-001';

UPDATE comentarios_por_partido SET estado_moderacion='REVIEW', reacciones=1 WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:10:00+0000' AND shard=3 AND creado_en='2030-06-08 20:12:15+0000' AND comentario_id='C-DEMO-001';
UPDATE comentarios_por_usuario SET estado_moderacion='REVIEW', reacciones=1 WHERE autor_id='U9999' AND dia_bucket='2030-06-08' AND creado_en='2030-06-08 20:12:15+0000' AND comentario_id='C-DEMO-001';

DELETE FROM comentarios_por_partido WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:10:00+0000' AND shard=3 AND creado_en='2030-06-08 20:12:15+0000' AND comentario_id='C-DEMO-001';
DELETE FROM comentarios_por_usuario WHERE autor_id='U9999' AND dia_bucket='2030-06-08' AND creado_en='2030-06-08 20:12:15+0000' AND comentario_id='C-DEMO-001';
