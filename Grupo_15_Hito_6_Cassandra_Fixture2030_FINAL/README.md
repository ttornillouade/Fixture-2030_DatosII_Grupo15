# Grupo 15 — Hito 6 — Comentarios Masivos en Cassandra

## Idea central
El diseño parte de patrones de acceso.

### Principal
```text
comentarios_por_partido
PK: ((partido_id, bucket_5m, shard), creado_en, comentario_id)
```

### Secundaria
```text
comentarios_por_usuario
PK: ((autor_id, dia_bucket), creado_en, comentario_id)
```

## Trade-off principal
Bucket de 5 minutos + 8 shards reduce concentración de escritura. El costo es consultar varios shards y fusionar el feed.

## Inicio
```bash
cp .env.example .env
docker compose up -d
bash scripts/init.sh
```

## Verificación
```bash
docker exec -it fixture2030-cassandra nodetool status
docker exec -it fixture2030-cassandra cqlsh
```

## CRUD
```bash
bash scripts/run_crud.sh
```

## Consultas
```bash
bash scripts/run_consultas.sh
```

## Feed multi-shard
```bash
python3 scripts/feed_multishard.py P001 "2030-06-08 20:00:00+0000" 20
```

## Volumen >1M
```bash
python3 scripts/generar_volumen.py 1100000
```

## Medición real
```bash
bash scripts/carga_volumen.sh 1100000
```
No se declara 10.000/s hasta medirlo.

## Evidencia
```bash
bash scripts/generar_evidencia.sh
```
Completar `docs/evidencia/README.md`.

## Persistencia
La consigna pide persistencia local en:
```text
~/docker/data/cassandra
```

## Laboratorio vs producción
El keyspace usa `NetworkTopologyStrategy` con RF=1 porque existe un solo nodo local. No representa alta disponibilidad. En producción, replicación y consistency levels deben definirse por operación.

## TTL
No se aplica TTL automático a la base principal para evitar expiración no requerida y generación innecesaria de tombstones.
