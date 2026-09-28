# Grupo 15 — Hito 7 — Redis Fixture 2030

Módulo de sesiones, caché y actividad temporal del Fixture 2030.

## Decisiones principales

```text
Sesión:
fixture2030:session:{session_id}
HASH + TTL 1800 s deslizante

Caché Equipo:
fixture2030:cache:equipo:{equipo_id}
HASH + TTL 300 s
cache-aside + invalidate-on-write

Ranking:
fixture2030:ranking:partidos:consultas:{fecha}
SORTED SET + ZINCRBY + TTL 48 h

Memoria:
maxmemory 256mb
maxmemory-policy noeviction
```

## Estructura

```text
Grupo_15_Hito_7_Redis_Fixture2030_FINAL/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Hito7.md
├── README.md
├── data/
│   └── fuente_verdad_equipos_demo.json
├── scripts/
│   ├── inicializacion.redis
│   ├── carga_muestra.redis
│   ├── sesiones.redis
│   ├── cache.redis
│   ├── concurrencia.redis
│   ├── metricas.redis
│   ├── init.sh
│   ├── run_sesiones.sh
│   ├── demo_expiracion.sh
│   ├── cache_aside.py
│   ├── demo_cache.sh
│   ├── prueba_concurrencia.sh
│   ├── prueba_rendimiento.sh
│   ├── generar_evidencia.sh
│   └── cleanup_fixture.sh
└── docs/
    ├── patrones_de_acceso.md
    ├── modelo_clave_valor.md
    ├── ciclo_de_vida_e_invalidacion.md
    ├── memoria_y_escalabilidad.md
    ├── rendimiento.md
    ├── coherencia_tpo.md
    ├── checklist_requisitos.md
    └── evidencia/
        └── README.md
```

## 1. Preparar

```bash
cp .env.example .env
docker compose config
```

## 2. Levantar Redis

```bash
docker compose up -d
docker compose ps
```

## 3. Inicializar muestra

```bash
bash scripts/init.sh
```

## 4. Probar sesiones

```bash
bash scripts/run_sesiones.sh
```

## 5. Ver expiración

```bash
bash scripts/demo_expiracion.sh
```

La política real es 30 minutos. La demo utiliza 5 segundos únicamente para poder observar el vencimiento.

## 6. Probar caché

```bash
bash scripts/demo_cache.sh
```

Demuestra:

```text
MISS -> fuente de verdad demo -> Redis
HIT
invalidación
MISS -> reconstrucción
```

## 7. Probar concurrencia

```bash
bash scripts/prueba_concurrencia.sh 10000 50
```

El score final de `P001` debe coincidir con los 10.000 incrementos.

## 8. Generar evidencia

```bash
bash scripts/generar_evidencia.sh
```

## 9. Benchmark

```bash
bash scripts/prueba_rendimiento.sh
```

Ejecución registrada el 27/09/2026:

```text
Redis 8.10.2
50.000 operaciones por prueba
50 clientes concurrentes

SET + TTL: 118.764,84 req/s — p50 0,335 ms
GET:       149.253,73 req/s — p50 0,175 ms
HSET:      105.708,25 req/s — p50 0,359 ms
```

Detalle e interpretación:

```text
docs/rendimiento.md
docs/evidencia/rendimiento_hito7_20260927_234301.txt
```

## 10. Abrir redis-cli

```bash
docker exec -it fixture2030-redis redis-cli
```

## 11. Ver claves sin `KEYS *`

```redis
SCAN 0 MATCH fixture2030:* COUNT 100
```

## 12. Reiniciar sin perder datos

```bash
docker compose down
docker compose up -d
```

La persistencia está montada en:

```text
~/docker/data/redis
```

## 13. Limpieza opcional

```bash
bash scripts/cleanup_fixture.sh
```

Solo elimina claves `fixture2030:*` mediante `SCAN` + `UNLINK`.
