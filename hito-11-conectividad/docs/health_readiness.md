# Health, readiness y diagnóstico por dependencia (5.6)

| Endpoint | Pregunta | Estado | Consulta bases |
|---|---|---|---|
| `GET /salud` | ¿El proceso de la API está vivo y atiende requests? (liveness) | **Implementado** | No |
| `GET /salud/dependencias` | ¿Cómo está cada base, vista desde la API? (diagnóstico) | **Implementado** | Sí, un ping por base |
| `GET /salud/listo` | ¿La API está preparada para recibir tráfico? (readiness) | **Propuesto** | Usaría el resultado del diagnóstico |

Ninguna request normal consulta otras bases: cada ruta usa solo la suya, y los chequeos de salud se
piden aparte.

## `GET /salud` — liveness (implementado)

Responde `{"estado": "up"}` sin tocar ninguna base. Si no responde, el problema es el proceso de la API
(caído, bloqueado o en otro puerto), no una dependencia. Es la primera prueba de `prueba_api.py`: si
falla, el resto de la cadena no se puede evaluar y se informa "API no alcanzable".

## `GET /salud/dependencias` — diagnóstico por dependencia (implementado)

```json
{"estado": "degraded",
 "dependencias": [{"nombre": "MongoDB", "estado": "down", "codigo": "DEPENDENCY_UNAVAILABLE", "ms": 3013.7},
                  {"nombre": "Neo4j", "estado": "up", "codigo": null, "ms": 52.5}, ...]}
```

| Base | Operación (mínima, no destructiva) | Qué valida además de la red |
|---|---|---|
| MongoDB | `ping` + existencia de la colección `equipos` | database configurada (MongoDB no da error si no existe) |
| Neo4j | `RETURN 1` por Bolt | autenticación y database por defecto |
| Cassandra | `SELECT release_version FROM system.local` | keyspace configurado (la sesión se abre sobre él) |
| Redis | `PING` | — (cualquier índice de db es válido) |
| InfluxDB | `SELECT 1` en la database configurada | token y database |
| IRIS | `SELECT 1` | usuario, contraseña y namespace (al conectar) |

**Estados de cada base:**
- `up`: la prueba terminó bien.
- `down`: se intentó y falló. `codigo` dice si fue rechazo (`DEPENDENCY_UNAVAILABLE`) o falta de respuesta (`DEPENDENCY_TIMEOUT`).
- `unknown`: falló de una forma no clasificada, así que no se puede afirmar el estado.
- `not_configured`: falta el secreto que necesita en `.env`.

**Estado global:**
- `up`: todas las bases configuradas están arriba.
- `degraded`: algunas están arriba y otras no.
- `down`: no hay ninguna arriba.

**Por qué responde 200 con bases caídas:** es un informe. El endpoint funcionó, y el estado de cada
base va en el cuerpo. Un 503 ahí impediría leer qué base falla. Las rutas de datos sí responden 503 o
504: no ocultan la falla con un 200.

**Costo y tiempos:**
- **Pings:** hace 6, en paralelo, y cada uno tiene el límite `TIMEOUT_S` = 3 s.
- **Duración:** con todo arriba tarda unos 150 ms. Con una base que no responde, como mucho 3 s.
- **Frecuencia:** no se llama en cada request. La pide un operador, el script del Hito 11 o un monitor externo.

## `GET /salud/listo` — readiness (propuesta, no implementada)

Indicaría si la API debe recibir tráfico. Se usaría en un balanceador o en el `healthcheck` de un
contenedor de la API.

| Aspecto | Propuesta | Por qué |
|---|---|---|
| Respuesta | 200 si está lista; 503 si no, con el mismo cuerpo que el diagnóstico | El orquestador solo mira el código; el cuerpo explica la causa |
| Criterio | Lista si al menos una base está `up` y ninguna está `not_configured` | Cada ruta usa una sola base: con una base caída, el resto de la API sigue sirviendo, y sus rutas ya responden 503/504. Sacar toda la API del tráfico por una base caída empeoraría la disponibilidad |
| Arranque | Al iniciar, no estar lista hasta el primer diagnóstico completo (incluido el contexto de MongoDB) | Detecta una configuración mal escrita (hallazgo 6) antes de recibir tráfico |
| Frecuencia | Recalcular cada 30 s en segundo plano y responder con el último resultado | La readiness se consulta seguido (cada 5–10 s); no debe disparar 6 pings por consulta |
| Timeout | El de cada ping (`TIMEOUT_S` = 3 s); el endpoint responde de inmediato con el resultado guardado | Un chequeo lento no puede bloquear al orquestador |
| Antigüedad | Incluir la fecha del último chequeo; si tiene más de 90 s, estado `unknown` | Un resultado viejo no es evidencia del estado actual |

## Otras mejoras propuestas (no implementadas)

| Mejora | Beneficio |
|---|---|
| *Circuit breaker* por base: después de N fallas seguidas, responder 503 sin intentar durante unos segundos | Una base colgada no ocupa hilos durante 3 s por request |
| Métricas por base (cantidad de 503/504, latencia) | Ver tendencias, no solo el estado puntual |
| API en un contenedor del mismo compose, con `healthcheck` sobre `/salud/listo` | Un solo comando para todo; las pruebas del Hito 11 correrían dentro de esa red |
