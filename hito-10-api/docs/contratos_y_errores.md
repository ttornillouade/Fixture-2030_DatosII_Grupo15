# Contratos, errores e idempotencia

## Contrato

El contrato se genera desde el código: `openapi/openapi.yaml` (`scripts/exportar_openapi.py`) y
Swagger UI en `http://localhost:8000/docs`. `scripts/ejecutar_pruebas.sh` verifica que el archivo
versionado coincida con las rutas implementadas.

## Validación (antes de consultar)

| Dato | Regla |
|---|---|
| `codigo` de partido | `^P[0-9]{3}$` |
| `codigo` / `equipoCodigo` de equipo | `^E[0-9]{3}$`; `equipoCodigo` es obligatorio en `/jugadores` |
| `posicion` | Arquero, Defensor, Mediocampista o Delantero |
| `limit` | 1 a 100 (por defecto 20) |
| `cursor` | El `nextCursor` recibido; si no es válido → 400 |
| `bucket` (comentarios) | Obligatorio, inicio de una ventana de 5 minutos |
| `desde`, `hasta` | Fechas ISO 8601; `desde < hasta`; máximo 15 min (`raw`) o 3 h (`minuto`) |
| `agregacion` | `raw` o `minuto` |
| `sesionId` | `^[A-Za-z0-9_-]{8,64}$` |
| Comentario | `usuarioId` `^U[0-9]{6}$`; `texto` de 1 a 500 caracteres |
| Estado | `EN_JUEGO` o `FINALIZADO` |

## Formato de error

```json
{ "code": "MATCH_NOT_FOUND", "message": "No existe el partido P999", "requestId": "req-3485866e66c6" }
```

Los errores de validación agregan `campos` con el detalle. Nunca se incluyen consultas, URIs,
credenciales ni trazas: el detalle técnico queda solo en el log.

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Parámetro, cuerpo o formato inválido |
| 404 | `TEAM_NOT_FOUND`, `MATCH_NOT_FOUND`, `SESSION_EXPIRED_OR_NOT_FOUND` | Recurso inexistente o sesión expirada |
| 409 | `ILLEGAL_TRANSITION` | El estado actual del partido no permite la transición |
| 503 | `DEPENDENCY_UNAVAILABLE` | La base no respondió dentro de `TIMEOUT_S` (3 s), está caída o rechazó las credenciales |
| 500 | `INTERNAL_ERROR` | Error no previsto |

**Vacío no es error:** una ventana sin observaciones (InfluxDB), un bucket sin comentarios o un
plantel vacío devuelven 200 con la lista vacía. Si la base falla, la respuesta es 503: nunca un 200 vacío.

## Lectura, escritura e idempotencia

| Endpoint | Tipo | Si se repite |
|---|---|---|
| Todos los `GET` | Lectura | Sin efectos |
| `POST /partidos/{codigo}/comentarios` | Creación | **No es idempotente:** cada request crea un comentario con id y fecha nuevos. Un reintento por respuesta perdida duplica el comentario (lo muestra la prueba `crear-repetido`). Decisión: se acepta, porque un comentario duplicado es visible y moderable; la mejora sería una clave `Idempotency-Key` guardada en Redis con TTL. La escritura en las 2 tablas es atómica (batch `LOGGED`): no quedan a medias |
| `POST /sesiones` | Creación | Crea otra sesión con otro id; las anteriores vencen solas por TTL |
| `DELETE /sesiones/{id}` | Invalidación | El efecto es idempotente: la segunda vez la sesión ya no existe y responde 404 |
| `PATCH /partidos/{codigo}/estado` | Actualización | Repetir la misma transición responde 409 (`EN_JUEGO → EN_JUEGO` no es válido): no hay doble efecto. La transición y su guardado ocurren en IRIS en una sola operación |
