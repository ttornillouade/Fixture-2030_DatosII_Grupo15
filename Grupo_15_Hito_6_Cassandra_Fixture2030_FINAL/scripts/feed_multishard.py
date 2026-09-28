#!/usr/bin/env python3
import csv,io,os,subprocess,sys
mid=sys.argv[1] if len(sys.argv)>1 else 'P001'; bucket=sys.argv[2] if len(sys.argv)>2 else '2030-06-08 20:00:00+0000'; limit=int(sys.argv[3]) if len(sys.argv)>3 else 20
c=os.getenv('CASSANDRA_CONTAINER_NAME','fixture2030-cassandra'); rows=[]
for shard in range(8):
 q=f"SELECT creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones FROM fixture2030_comments.comentarios_por_partido WHERE partido_id='{mid}' AND bucket_5m='{bucket}' AND shard={shard} LIMIT {limit};"
 r=subprocess.run(['docker','exec',c,'cqlsh','--csv','-e',q],capture_output=True,text=True,check=True)
 rows.extend(csv.DictReader(io.StringIO(r.stdout)))
rows.sort(key=lambda x:(x.get('creado_en',''),x.get('comentario_id','')), reverse=True)
for r in rows[:limit]: print(r)
