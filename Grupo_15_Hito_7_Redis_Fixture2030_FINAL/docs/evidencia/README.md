# Evidencia — Hito 7

No se incluyen resultados inventados.

## Evidencia funcional

Ejecutar:

```bash
bash scripts/generar_evidencia.sh
```

Debe registrar:

- Docker y versión;
- `PING`;
- política de memoria;
- CRUD de sesión;
- TTL observado;
- expiración real de una clave;
- cache MISS/HIT;
- invalidación y reconstrucción;
- prueba concurrente;
- ranking;
- métricas.

## Rendimiento

Ejecutar:

```bash
bash scripts/prueba_rendimiento.sh
```

Guardar el archivo generado en esta carpeta.

## Capturas opcionales útiles

- `docker compose ps`;
- `TTL fixture2030:session:...`;
- cache HIT/MISS;
- `ZREVRANGE ... WITHSCORES`;
- `INFO memory`;
- `CONFIG GET maxmemory-policy`.

Registrar además los recursos de Docker/Mac usados en la medición.
