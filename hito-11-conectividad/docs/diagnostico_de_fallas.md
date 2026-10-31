# Diagnóstico de fallas

## Comportamiento de la API ante cada falla (RF17, RF18)

| Situación | Cómo se provoca | Respuesta de la API | Tiempo máximo |
|---|---|---|---|
| Operación exitosa | — | 200 con datos | — |
| Ausencia válida | recurso inexistente | 404 (`TEAM_NOT_FOUND`, `MATCH_NOT_FOUND`, `PLAYER_NOT_FOUND`, `SESSION_EXPIRED_OR_NOT_FOUND`) | — |
| Respuesta vacía válida | plantel, ventana o bucket sin datos | 200 con lista vacía | — |
| Error de validación | parámetro fuera del contrato | 400 `VALIDATION_ERROR` (no llega a la base) | — |
| Dependencia caída o rechazada | `docker stop` | 503 `DEPENDENCY_UNAVAILABLE` | 3 s en MongoDB (el driver reintenta la selección de servidor); milisegundos en el resto |
| Dependencia lenta o colgada | `docker pause` | 504 `DEPENDENCY_TIMEOUT` | `TIMEOUT_S` = 3 s |
| No autenticada | credencial inválida | 503 `DEPENDENCY_UNAVAILABLE` (Neo4j `AuthError`, InfluxDB 401, IRIS `Access Denied`) | — |
| Contexto inexistente | database, keyspace o namespace mal escrito | 503 en Cassandra, InfluxDB e IRIS; **404 en MongoDB** (ver hallazgo 6) | — |
| Error interno | excepción no prevista | 500 `INTERNAL_ERROR`, con el detalle solo en el log | — |
| API no alcanzable | API detenida | sin respuesta HTTP: `prueba_api.py` lo informa como "API no alcanzable" | — |

Ningún error expone URIs, consultas, credenciales ni trazas. Cada respuesta lleva `requestId`
(también en el header `X-Request-ID`), y el log registra **una sola línea por request** con la base,
el resultado, la duración, la causa técnica y el `requestId`:

```text
GET /equipos/E010 fuente=MongoDB status=503 3308ms causa=ServerSelectionTimeoutError (conexión rechazada) req-11c5d7a1b21e
GET /partidos/P001/detalle fuente=IRIS status=504 3007ms causa=sin respuesta en 3 s (límite de la API) req-052f352276b0
GET /salud/dependencias fuente=Salud status=200 3012ms causa=Redis: ConnectionError; IRIS: sin respuesta en 3 s (límite de la API) req-4923873d9a36
```

La causa es el tipo de excepción del driver (o el código HTTP de InfluxDB): queda en el log y nunca
en la respuesta. No hay reintentos: la API no reintenta y el driver de Neo4j tiene los reintentos
desactivados (`max_transaction_retry_time=0`).

## Hallazgos de la evaluación

### 1. MongoDB tardaba 8,6 s en fallar (límite configurado: 3 s)
- **Hipótesis:** los timeouts del driver se suman por etapa (selección de servidor, conexión, socket).
- **Prueba:** `docker pause fixture2030-mongodb` y `GET /equipos/E010`.
- **Resultado:** 503 a los 8,6 s, con `_OperationCancelled`.
- **Corrección:** `timeoutMS=3000` en el cliente, que limita la operación completa. Ahora responde en 3,0 s.

### 2. Neo4j e IRIS bloqueaban la request mientras la base estaba colgada
- **Hipótesis:** sus drivers limitan la conexión, pero no la lectura.
- **Prueba:** `docker pause` de cada uno y la ruta correspondiente, con un límite de 20 s en `curl`.
- **Resultado:** la request quedó esperando los 20 s y terminó con 200 cuando se reanudó la base.
  El `timeout` de `execute_query` de Neo4j limita la transacción en el servidor, no la espera del cliente.
- **Corrección:** `hito-10-api/app/adaptadores/limite.py` ejecuta esas operaciones en un hilo y responde
  504 al vencer `TIMEOUT_S`. La operación sigue en el hilo hasta que la base responde o corta.
- **Consecuencia:** en un `PATCH` que vence, el resultado es desconocido (la base puede aplicarlo
  después). Antes de reintentar hay que consultar el estado; queda documentado en el contrato.

### 3. Timeout y dependencia no disponible devolvían el mismo 503
- **Prueba:** detener y pausar cada base.
- **Resultado:** las seis respondían 503 en los dos casos. La consigna pide distinguirlos (RF18).
- **Corrección:** 504 `DEPENDENCY_TIMEOUT` cuando la base acepta la conexión y no responde. Cada
  adaptador lo decide con la excepción de su driver (`hito-10-api/docs/arquitectura_y_adaptadores.md`).

### 4. MongoDB detenido se informaba como timeout
- **Hipótesis:** con la base detenida, el driver reintenta hasta agotar `timeoutMS` y lanza
  `ServerSelectionTimeoutError`, que es un error de timeout aunque la causa sea un rechazo.
- **Prueba:** leer `topology_description` del cliente después del error.
- **Resultado:** el último error de conexión era `Connection refused`, no `NetworkTimeout`.
- **Corrección:** si la conexión fue rechazada, la API responde 503; si no hubo respuesta, 504.

### 5. Neo4j colgado se informaba como no disponible
- **Prueba:** `docker pause fixture2030-neo4j`; el error del driver fue `ServiceUnavailable`.
- **Resultado:** el mensaje decía `Failed to read four byte Bolt handshake response`: el TCP conectó
  (el `docker-proxy` acepta) y el handshake no respondió. Con la base detenida, el mensaje es *refused*.
- **Corrección:** un handshake sin respuesta es 504. La ruta y `/salud/dependencias` ahora coinciden.

### 6. Una database de MongoDB mal escrita quedaba oculta
- **Hipótesis:** MongoDB no valida que la database exista al leer.
- **Prueba:** contraste "database inexistente (fixture2030_x)" de `prueba_clientes.py`, con el mismo
  driver que la API.
- **Resultado:** la red, el driver y el handshake funcionan; `find_one` devuelve `None` y la database
  no figura en el listado. La ruta de la API usa esa misma lectura, así que con esa configuración
  `GET /equipos/E010` respondería **404**, como si el equipo no existiera. Es una falla de
  configuración que la ruta no puede distinguir de una ausencia sin una consulta extra por request.
- **Corrección:** el ping de `/salud/dependencias` verifica que exista la colección `equipos`: el
  diagnóstico marca MongoDB como `down` aunque la ruta responda 404.
- **Siguiente paso propuesto:** que la readiness use ese chequeo al arrancar la API (`health_readiness.md`).

### 7. El nombre del servicio de Compose no existe desde la notebook
- **Prueba:** resolver `mongodb` desde la notebook.
- **Resultado:** *host no resuelto*. Ese nombre solo existe en la red `hito-10-api_default`.
- **Siguiente paso:** si la API pasa a un contenedor, cambiar los hosts del `.env` a los nombres de los servicios.

### 8. Un puerto abierto no es una prueba del producto
- **Prueba:** TCP a `localhost:7000`, el puerto interno de gossip de Cassandra (no publicado).
- **Resultado:** la conexión TCP funciona, porque en macOS ese puerto lo usa AirPlay. El driver CQL
  contra ese puerto falla con `NoHostAvailable`. Por eso la matriz no da `up` con solo el TCP.

### 9. El cliente no distingue algunos errores de contexto
- **Cassandra:** un keyspace inexistente llega como `NoHostAvailable`, igual que una red caída; la
  diferencia está en el mensaje (nombra el keyspace) y en que falla de inmediato.
- **IRIS:** un namespace inexistente y un usuario inexistente responden el mismo `Access Denied`. Se
  distinguen consultando `%SYS.Namespace.Exists` con una identidad válida.
- **Redis:** una clave expirada y una ausente son iguales (`EXISTS 0`, `TTL -2`); la API responde 404
  `SESSION_EXPIRED_OR_NOT_FOUND` en los dos casos, y 503/504 solo si Redis no responde.

## Escenarios de falla controlada (5.7, RF20, RF21)

Se ejecutan con `scripts/prueba_falla.sh`. Ninguno borra datos ni
volúmenes: `docker stop` y `docker pause` son reversibles, y cada escenario compara una huella de los
datos y los montajes antes y después.

Resultados del 2026-10-30, commit `064e2b5` (`evidencia/falla_<accion>_<producto>.txt`):

| Escenario | Durante la falla | Línea de log | TCP desde la notebook | `/salud/dependencias` | Recuperación | Después |
|---|---|---|---|---|---|---|
| `detener redis` | 503 en 3 ms | `status=503 causa=ConnectionError` | *refused* | `degraded`, Redis `down` (503) | 200 a 1 s, sin reiniciar la API | Misma huella; la sesión sobrevive (AOF del Hito 7) |
| `detener mongodb` | 503 en 3,3 s | `status=503 causa=ServerSelectionTimeoutError (conexión rechazada)` | *refused* | `degraded`, MongoDB `down` (503) | 200 a 1 s | Misma huella y montajes |
| `pausar neo4j` | 504 en 3,0 s | `status=504 causa=sin respuesta en 3 s (límite de la API)` | **conecta** | `degraded`, Neo4j `down` (504) | 200 de inmediato | Misma huella y montajes |
| `pausar iris` | 504 en 3,0 s | `status=504 causa=sin respuesta en 3 s (límite de la API)` | **conecta** | `degraded`, IRIS `down` (504) | 200 de inmediato | Misma huella y montajes |

Durante cada falla, otra ruta de una base distinta siguió respondiendo 200. Con la base pausada, el
TCP conecta (lo atiende el `docker-proxy`): solo el protocolo muestra que la base no responde. MongoDB
tarda 3 s incluso detenido porque el driver reintenta la selección de servidor hasta agotar el límite.

## Pruebas no realizadas

- **Credencial inválida en la API:** se probó con el driver (Neo4j, InfluxDB, IRIS) y no levantando
  la API con una contraseña errónea. Con IRIS, varios intentos fallidos pueden deshabilitar `_SYSTEM`.
- **Puerto no publicado para la API:** equivale a la base detenida desde el punto de vista de la API
  (*connection refused*). Se mostró con la prueba TCP, sin modificar el `compose.yaml`.
- **Timeout demasiado bajo:** no se cambió `TIMEOUT_S`; el escenario `pausar` ya muestra el corte por límite.
