# Matriz de conectividad

La matriz se genera en cada ejecución de `scripts/evaluar_conectividad.sh` y queda en
[`evidencia/matriz.md`](evidencia/matriz.md), con fecha, commit, modo y productos evaluados. El
detalle de cada prueba (resultado, duración, diagnóstico) está en `evidencia/resultados_*.txt` y en
`evidencia/resultados.jsonl`.

## Capas de evaluación (5.2)

Cada producto se evalúa de menor a mayor costo. Una capa que falla deja de lado las siguientes del
mismo destino, porque su resultado ya no sería interpretable.

| Capa | Pregunta que responde | Lo que todavía no permite concluir |
|---|---|---|
| Configuración | ¿Están todas las variables que usa la API? (secretos: solo si están definidos) | Que los valores sean correctos |
| Resolución | ¿El host se convierte en una dirección desde la notebook? | Que haya algo escuchando |
| TCP | ¿Hay un listener en ese host y puerto? (conexión, *refused*, *timeout*, no resuelto) | Que el listener sea el producto, ni que responda |
| Protocolo | ¿Responde el handshake del producto (hello, Bolt, CQL, RESP, HTTP, Superserver)? | Que la identidad sea válida |
| Autenticación | ¿La identidad configurada es aceptada? | Que pueda leer el contexto |
| Autorización | ¿Esa identidad tiene permiso sobre el recurso? | Que el contexto exista |
| Contexto | ¿Existe la database, keyspace, namespace o tabla configurada? | Que haya datos o que la consulta sea válida |
| Lectura | ¿Una lectura mínima, acotada y no destructiva funciona? | Rendimiento o disponibilidad sostenida |
| API | ¿La ruta del Hito 10 recorre cliente → API → adaptador → producto? | Rendimiento o capacidad bajo carga |

Cuando el laboratorio no tiene autenticación (MongoDB, Cassandra, Redis), esas capas quedan en
**SKIP**: no se pudieron ejecutar por falta de configuración, no significa que el producto esté caído.
Lo mismo con los CLI nativos que no están instalados en la notebook.

## Estados

| Estado | Significado en esta matriz |
|---|---|
| `up` | Todas las capas probadas, hasta la lectura (y la API, si se probó), dieron OK |
| `down` | Se intentó una capa y falló. El diagnóstico es la primera capa que falló |
| `degraded` | El producto responde a su cliente pero la ruta de la API falla, o al revés |
| `unknown` | Desconocido: se probó algo, pero no alcanza para concluir. Por ejemplo, con `--modo tcp` el puerto abre, pero no se sabe si la base responde |
| `not_tested` | No probado: en esa corrida no se ejecutó ninguna prueba del producto (`--producto` lo dejó afuera) |
| `not_configured` | Faltan variables: el módulo no está preparado en ese entorno |

En las pruebas individuales, `OK` significa que **esa prueba concreta** dio el resultado esperado
(RNF17): no es una garantía de rendimiento ni de disponibilidad permanente. Los **contrastes** son casos
negativos (credencial, contexto o recurso equivocados): son `OK` si fallan exactamente de la forma
esperada, y se cuentan aparte para que no cambien el estado del producto.

## Última ejecución

Copia de [`evidencia/matriz.md`](evidencia/matriz.md) del 2026-10-30, con las seis bases y la API corriendo:

Commit 064e2b5; modo completo; productos: todos; origen: notebook.

| Producto | Estado | TCP | Lectura | API | Capas OK / FALLA / SKIP | Contrastes OK / FALLA | Diagnóstico |
|---|---|---|---|---|---|---|---|
| mongodb | **up** | 1 ms | 1 ms | 8 ms | 7 / 0 / 3 | 8 / 0 | todas las capas probadas respondieron |
| neo4j | **up** | 1 ms | 57 ms | 23 ms | 13 / 0 / 1 | 4 / 0 | todas las capas probadas respondieron |
| cassandra | **up** | 0 ms | 12 ms | 11 ms | 7 / 0 / 3 | 6 / 0 | todas las capas probadas respondieron |
| redis | **up** | 0 ms | 1 ms | 6 ms | 8 / 0 / 2 | 2 / 0 | todas las capas probadas respondieron |
| influxdb | **up** | 0 ms | 46 ms | 19 ms | 9 / 0 / 1 | 4 / 0 | todas las capas probadas respondieron |
| iris | **up** | 0 ms | 2 ms | 9 ms | 13 / 0 / 1 | 4 / 0 | todas las capas probadas respondieron |
| api | **up** | — | — | 82 ms | 2 / 0 / 0 | 0 / 0 | todas las capas probadas respondieron |

Latencias: la máxima de cada capa en esta ejecución. Miden una prueba puntual, no rendimiento (RNF17).

Los SKIP son las capas de autenticación y autorización que el laboratorio no tiene configuradas
(MongoDB, Cassandra, Redis) y los CLI nativos que no están instalados en la notebook.

## Qué distingue cada producto (contrastes)

| Producto | Casos que la evaluación separa |
|---|---|
| MongoDB | Documento inexistente (`None`, la API da 404) ≠ database inexistente (también vacío: MongoDB no da error) ≠ base caída |
| Neo4j | Browser HTTP accesible ≠ Bolt; usuario rechazado ≠ database inexistente (`DatabaseNotFound`) ≠ jugador inexistente (0 filas) |
| Cassandra | Keyspace inexistente (el driver lo informa como `NoHostAvailable`, con el keyspace en el mensaje) ≠ consulta inválida (`InvalidRequest` inmediato) ≠ timeout; puerto que no habla CQL |
| Redis | Clave ausente (`EXISTS 0`, `TTL -2`) ≠ Redis caído. Una clave expirada responde igual que una ausente |
| InfluxDB | `/health` accesible ≠ token inválido (401) ≠ database inexistente (404) ≠ ventana sin puntos (200 vacío) |
| IRIS | Portal HTTP accesible ≠ Superserver; usuario inexistente y namespace inexistente dan el **mismo** `Access Denied` (se distinguen con `%SYS.Namespace.Exists`); partido inexistente (0 filas) |
