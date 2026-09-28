#!/usr/bin/env python3
import csv, datetime as dt, sys
from pathlib import Path
TOTAL=int(sys.argv[1]) if len(sys.argv)>1 else 1_100_000
OUT=Path('data'); OUT.mkdir(exist_ok=True)
main=OUT/'comentarios_por_partido.csv'; user=OUT/'comentarios_por_usuario.csv'
base=dt.datetime(2030,6,8,18,0,0); popular=[f'P{i:03d}' for i in range(1,9)]
fm=['partido_id','bucket_5m','shard','creado_en','comentario_id','autor_id','contenido','estado_moderacion','reacciones']
fu=['autor_id','dia_bucket','creado_en','comentario_id','partido_id','bucket_5m','shard','contenido','estado_moderacion','reacciones']
with main.open('w',newline='',encoding='utf-8') as a, user.open('w',newline='',encoding='utf-8') as b:
    wm=csv.DictWriter(a,fieldnames=fm); wu=csv.DictWriter(b,fieldnames=fu); wm.writeheader(); wu.writeheader()
    for i in range(TOTAL):
        partido=popular[(i//2)%8] if i%2==0 else f'P{((i//2)%127)+1:03d}'
        creado=base+dt.timedelta(seconds=i%10800); bm=(creado.minute//5)*5; bucket=creado.replace(minute=bm,second=0,microsecond=0)
        cid=f'C{i+1:09d}'; autor=f'U{(i%50000)+1:06d}'; shard=i%8
        estado='BLOCKED' if i%997==0 else 'REVIEW' if i%211==0 else 'VISIBLE'
        contenido=f'Comentario sintetico {i+1} sobre {partido}'; reacciones=i%20
        row=dict(partido_id=partido,bucket_5m=bucket.isoformat(sep=' '),shard=shard,creado_en=creado.isoformat(sep=' '),comentario_id=cid,autor_id=autor,contenido=contenido,estado_moderacion=estado,reacciones=reacciones)
        wm.writerow(row)
        wu.writerow(dict(autor_id=autor,dia_bucket=creado.date().isoformat(),creado_en=row['creado_en'],comentario_id=cid,partido_id=partido,bucket_5m=row['bucket_5m'],shard=shard,contenido=contenido,estado_moderacion=estado,reacciones=reacciones))
print(f'Generados {TOTAL:,} comentarios')
print(main); print(user)
