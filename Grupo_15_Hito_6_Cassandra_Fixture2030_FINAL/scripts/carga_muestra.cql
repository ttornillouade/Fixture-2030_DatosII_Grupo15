CONSISTENCY ONE;

USE fixture2030_comments;



// Carga pequeña determinística. Reejecutar realiza upserts sobre las mismas PK.

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',0,'2030-06-08 20:00:00+0000','C000001','U0001','Comentario de muestra 1 para P001','VISIBLE',1);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0001','2030-06-08','2030-06-08 20:00:00+0000','C000001','P001','2030-06-08 20:00:00+0000',0,'Comentario de muestra 1 para P001','VISIBLE',1);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',1,'2030-06-08 20:00:17+0000','C000002','U0002','Comentario de muestra 2 para P001','VISIBLE',2);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0002','2030-06-08','2030-06-08 20:00:17+0000','C000002','P001','2030-06-08 20:00:00+0000',1,'Comentario de muestra 2 para P001','VISIBLE',2);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',2,'2030-06-08 20:00:34+0000','C000003','U0003','Comentario de muestra 3 para P001','VISIBLE',3);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0003','2030-06-08','2030-06-08 20:00:34+0000','C000003','P001','2030-06-08 20:00:00+0000',2,'Comentario de muestra 3 para P001','VISIBLE',3);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',3,'2030-06-08 20:00:51+0000','C000004','U0004','Comentario de muestra 4 para P001','VISIBLE',4);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0004','2030-06-08','2030-06-08 20:00:51+0000','C000004','P001','2030-06-08 20:00:00+0000',3,'Comentario de muestra 4 para P001','VISIBLE',4);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',4,'2030-06-08 20:01:08+0000','C000005','U0005','Comentario de muestra 5 para P001','VISIBLE',5);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0005','2030-06-08','2030-06-08 20:01:08+0000','C000005','P001','2030-06-08 20:00:00+0000',4,'Comentario de muestra 5 para P001','VISIBLE',5);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',5,'2030-06-08 20:01:25+0000','C000006','U0006','Comentario de muestra 6 para P001','VISIBLE',0);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0006','2030-06-08','2030-06-08 20:01:25+0000','C000006','P001','2030-06-08 20:00:00+0000',5,'Comentario de muestra 6 para P001','VISIBLE',0);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',6,'2030-06-08 20:01:42+0000','C000007','U0007','Comentario de muestra 7 para P001','REVIEW',1);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0007','2030-06-08','2030-06-08 20:01:42+0000','C000007','P001','2030-06-08 20:00:00+0000',6,'Comentario de muestra 7 para P001','REVIEW',1);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',7,'2030-06-08 20:01:59+0000','C000008','U0008','Comentario de muestra 8 para P001','VISIBLE',2);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0008','2030-06-08','2030-06-08 20:01:59+0000','C000008','P001','2030-06-08 20:00:00+0000',7,'Comentario de muestra 8 para P001','VISIBLE',2);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',0,'2030-06-08 20:02:16+0000','C000009','U0009','Comentario de muestra 9 para P001','VISIBLE',3);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0009','2030-06-08','2030-06-08 20:02:16+0000','C000009','P001','2030-06-08 20:00:00+0000',0,'Comentario de muestra 9 para P001','VISIBLE',3);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',1,'2030-06-08 20:02:33+0000','C000010','U0010','Comentario de muestra 10 para P001','VISIBLE',4);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0010','2030-06-08','2030-06-08 20:02:33+0000','C000010','P001','2030-06-08 20:00:00+0000',1,'Comentario de muestra 10 para P001','VISIBLE',4);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',2,'2030-06-08 20:02:50+0000','C000011','U0011','Comentario de muestra 11 para P001','VISIBLE',5);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0011','2030-06-08','2030-06-08 20:02:50+0000','C000011','P001','2030-06-08 20:00:00+0000',2,'Comentario de muestra 11 para P001','VISIBLE',5);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',3,'2030-06-08 20:03:07+0000','C000012','U0012','Comentario de muestra 12 para P001','VISIBLE',0);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0012','2030-06-08','2030-06-08 20:03:07+0000','C000012','P001','2030-06-08 20:00:00+0000',3,'Comentario de muestra 12 para P001','VISIBLE',0);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',4,'2030-06-08 20:03:24+0000','C000013','U0001','Comentario de muestra 13 para P001','VISIBLE',1);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0001','2030-06-08','2030-06-08 20:03:24+0000','C000013','P001','2030-06-08 20:00:00+0000',4,'Comentario de muestra 13 para P001','VISIBLE',1);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',5,'2030-06-08 20:03:41+0000','C000014','U0002','Comentario de muestra 14 para P001','VISIBLE',2);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0002','2030-06-08','2030-06-08 20:03:41+0000','C000014','P001','2030-06-08 20:00:00+0000',5,'Comentario de muestra 14 para P001','VISIBLE',2);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',6,'2030-06-08 20:03:58+0000','C000015','U0003','Comentario de muestra 15 para P001','VISIBLE',3);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0003','2030-06-08','2030-06-08 20:03:58+0000','C000015','P001','2030-06-08 20:00:00+0000',6,'Comentario de muestra 15 para P001','VISIBLE',3);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',7,'2030-06-08 20:04:15+0000','C000016','U0004','Comentario de muestra 16 para P001','VISIBLE',4);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0004','2030-06-08','2030-06-08 20:04:15+0000','C000016','P001','2030-06-08 20:00:00+0000',7,'Comentario de muestra 16 para P001','VISIBLE',4);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',0,'2030-06-08 20:04:32+0000','C000017','U0005','Comentario de muestra 17 para P001','VISIBLE',5);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0005','2030-06-08','2030-06-08 20:04:32+0000','C000017','P001','2030-06-08 20:00:00+0000',0,'Comentario de muestra 17 para P001','VISIBLE',5);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:00:00+0000',1,'2030-06-08 20:04:49+0000','C000018','U0006','Comentario de muestra 18 para P001','VISIBLE',0);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0006','2030-06-08','2030-06-08 20:04:49+0000','C000018','P001','2030-06-08 20:00:00+0000',1,'Comentario de muestra 18 para P001','VISIBLE',0);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:05:00+0000',2,'2030-06-08 20:05:06+0000','C000019','U0007','Comentario de muestra 19 para P001','REVIEW',1);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0007','2030-06-08','2030-06-08 20:05:06+0000','C000019','P001','2030-06-08 20:05:00+0000',2,'Comentario de muestra 19 para P001','REVIEW',1);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:05:00+0000',3,'2030-06-08 20:05:23+0000','C000020','U0008','Comentario de muestra 20 para P001','VISIBLE',2);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0008','2030-06-08','2030-06-08 20:05:23+0000','C000020','P001','2030-06-08 20:05:00+0000',3,'Comentario de muestra 20 para P001','VISIBLE',2);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:05:00+0000',4,'2030-06-08 20:05:40+0000','C000021','U0009','Comentario de muestra 21 para P001','VISIBLE',3);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0009','2030-06-08','2030-06-08 20:05:40+0000','C000021','P001','2030-06-08 20:05:00+0000',4,'Comentario de muestra 21 para P001','VISIBLE',3);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:05:00+0000',5,'2030-06-08 20:05:57+0000','C000022','U0010','Comentario de muestra 22 para P001','VISIBLE',4);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0010','2030-06-08','2030-06-08 20:05:57+0000','C000022','P001','2030-06-08 20:05:00+0000',5,'Comentario de muestra 22 para P001','VISIBLE',4);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:05:00+0000',6,'2030-06-08 20:06:14+0000','C000023','U0011','Comentario de muestra 23 para P001','BLOCKED',5);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0011','2030-06-08','2030-06-08 20:06:14+0000','C000023','P001','2030-06-08 20:05:00+0000',6,'Comentario de muestra 23 para P001','BLOCKED',5);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P001','2030-06-08 20:05:00+0000',7,'2030-06-08 20:06:31+0000','C000024','U0012','Comentario de muestra 24 para P001','VISIBLE',0);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0012','2030-06-08','2030-06-08 20:06:31+0000','C000024','P001','2030-06-08 20:05:00+0000',7,'Comentario de muestra 24 para P001','VISIBLE',0);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',0,'2030-06-08 20:06:48+0000','C000025','U0001','Comentario de muestra 25 para P002','VISIBLE',1);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0001','2030-06-08','2030-06-08 20:06:48+0000','C000025','P002','2030-06-08 20:05:00+0000',0,'Comentario de muestra 25 para P002','VISIBLE',1);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',1,'2030-06-08 20:07:05+0000','C000026','U0002','Comentario de muestra 26 para P002','VISIBLE',2);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0002','2030-06-08','2030-06-08 20:07:05+0000','C000026','P002','2030-06-08 20:05:00+0000',1,'Comentario de muestra 26 para P002','VISIBLE',2);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',2,'2030-06-08 20:07:22+0000','C000027','U0003','Comentario de muestra 27 para P002','VISIBLE',3);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0003','2030-06-08','2030-06-08 20:07:22+0000','C000027','P002','2030-06-08 20:05:00+0000',2,'Comentario de muestra 27 para P002','VISIBLE',3);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',3,'2030-06-08 20:07:39+0000','C000028','U0004','Comentario de muestra 28 para P002','VISIBLE',4);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0004','2030-06-08','2030-06-08 20:07:39+0000','C000028','P002','2030-06-08 20:05:00+0000',3,'Comentario de muestra 28 para P002','VISIBLE',4);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',4,'2030-06-08 20:07:56+0000','C000029','U0005','Comentario de muestra 29 para P002','VISIBLE',5);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0005','2030-06-08','2030-06-08 20:07:56+0000','C000029','P002','2030-06-08 20:05:00+0000',4,'Comentario de muestra 29 para P002','VISIBLE',5);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',5,'2030-06-08 20:08:13+0000','C000030','U0006','Comentario de muestra 30 para P002','VISIBLE',0);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0006','2030-06-08','2030-06-08 20:08:13+0000','C000030','P002','2030-06-08 20:05:00+0000',5,'Comentario de muestra 30 para P002','VISIBLE',0);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',6,'2030-06-08 20:08:30+0000','C000031','U0007','Comentario de muestra 31 para P002','VISIBLE',1);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0007','2030-06-08','2030-06-08 20:08:30+0000','C000031','P002','2030-06-08 20:05:00+0000',6,'Comentario de muestra 31 para P002','VISIBLE',1);

INSERT INTO comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) VALUES ('P002','2030-06-08 20:05:00+0000',7,'2030-06-08 20:08:47+0000','C000032','U0008','Comentario de muestra 32 para P002','VISIBLE',2);

INSERT INTO comentarios_por_usuario (autor_id,dia_bucket,creado_en,comentario_id,partido_id,bucket_5m,shard,contenido,estado_moderacion,reacciones) VALUES ('U0008','2030-06-08','2030-06-08 20:08:47+0000','C000032','P002','2030-06-08 20:05:00+0000',7,'Comentario de muestra 32 para P002','VISIBLE',2);