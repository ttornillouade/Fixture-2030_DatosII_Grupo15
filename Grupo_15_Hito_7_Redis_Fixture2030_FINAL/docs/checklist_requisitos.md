# Checklist — Hito 7

| Requisito | Implementación |
|---|---|
| RF1 | `docker-compose.yml`, `scripts/init.sh` |
| RF2 | `docs/patrones_de_acceso.md` |
| RF3 | `scripts/sesiones.redis`, `run_sesiones.sh` |
| RF4 | TTL 1800 s + `demo_expiracion.sh` |
| RF5 | Hash de sesión con user, timestamps y estado |
| RF6 | caché de `Equipo` |
| RF7 | `cache_aside.py`, `demo_cache.sh` |
| RF8 | `ZINCRBY` + `prueba_concurrencia.sh` |
| RF9 | Sorted Set de ranking temporal |
| RF10 | `maxmemory 256mb`, `noeviction` |
| RF11 | `carga_muestra.redis` + JSON reproducible |
| RF12 | `prueba_rendimiento.sh` |
| RF13 | `generar_evidencia.sh`, `docs/evidencia/` |
| RNF1 | `redis:latest` |
| RNF2 | `${HOME}/docker/data/redis` |
| RNF3 | README + scripts |
| RNF4 | cada clave vinculada a un patrón |
| RNF5 | namespace `fixture2030:*` |
| RNF6 | TTL/invalidation/lifecycle documentados |
| RNF7 | sin secretos reales |
| RNF8 | `SCAN`, no `KEYS *` |
| RNF9 | scripts separados por responsabilidad |
| RNF10 | evidencia con fecha, versión y recursos |
