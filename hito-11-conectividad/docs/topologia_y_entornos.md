# Topología y entornos

## Dónde corre cada cosa

```text
Notebook (macOS, Apple Silicon)
├── API del Hito 10 ─ uvicorn, 127.0.0.1:8000 ─┐
├── Scripts del Hito 11 (mismos drivers) ───────┤  se conectan a localhost:<puerto publicado>
│                                               ▼
│   Docker Desktop: puertos publicados solo en 127.0.0.1 (docker-proxy)
│   └── red de Compose "hito-10-api_default" (hito-10-api/compose.yaml)
│       ├── mongodb    fixture2030-mongodb    27017
│       ├── neo4j      fixture2030-neo4j      7687 (Bolt), 7474 (HTTP)
│       ├── cassandra  fixture2030-cassandra  9042 (CQL)
│       ├── redis      fixture2030-redis      6379
│       ├── influxdb   fixture2030-influxdb   8181
│       └── iris       fixture2030-iris       1972 (Superserver), 52773 (HTTP)
└── Datos persistentes: ~/docker/data/<base> (montajes del compose)
```

La API **no** corre en un contenedor: corre en la notebook y llega a las bases por los puertos que
Compose publica. Las pruebas del Hito 11 corren en el **mismo entorno que la API** (RNF3), así que
`localhost` significa lo mismo para las dos: la notebook.

## Puertos publicados e internos

| Servicio | Puerto interno (en la red de Compose) | Publicado en la notebook | Host desde la notebook | Host desde otro contenedor de la red |
|---|---|---|---|---|
| mongodb | 27017 | `127.0.0.1:27017` | `localhost` | `mongodb` |
| neo4j | 7687, 7474 | `127.0.0.1:7687`, `127.0.0.1:7474` | `localhost` | `neo4j` |
| cassandra | 9042 (y 7000, 7199, internos) | `127.0.0.1:9042` (7000 y 7199 **no**) | `localhost` | `cassandra` |
| redis | 6379 | `127.0.0.1:6379` | `localhost` | `redis` |
| influxdb | 8181 | `127.0.0.1:8181` | `localhost` | `influxdb` |
| iris | 1972, 52773 | `127.0.0.1:1972`, `127.0.0.1:52773` | `localhost` | `iris` |

Los puertos se publican solo en `127.0.0.1`: no son accesibles desde otra máquina de la red.

## Qué significa `localhost` en cada entorno

| Desde | `localhost` es | Cómo llega a MongoDB |
|---|---|---|
| La notebook (API, scripts del Hito 11) | la notebook | `localhost:27017` (puerto publicado) |
| Un contenedor de la red `hito-10-api_default` | ese mismo contenedor | `mongodb:27017` (nombre del servicio) |
| Dentro de `fixture2030-mongodb` (`docker exec`) | el contenedor de MongoDB | `localhost:27017`, pero es **otro origen**: no prueba lo que ve la API |

Por eso las pruebas nativas del Hito 11 usan los drivers desde la notebook y no `docker exec`: un
`mongosh` dentro del contenedor puede funcionar aunque el puerto no esté publicado.

## Lo que mostró la evaluación sobre la topología

- **El nombre del servicio no existe en la notebook.** `mongodb:27017` da *host no resuelto*: solo la
  red de Compose lo resuelve (prueba de contraste en `resultados_tcp.txt`). Si la API pasara a un
  contenedor, habría que cambiar `MONGODB_URI` y el resto de los hosts a los nombres de los servicios.
- **`localhost` resuelve primero a `::1` (IPv6).** Docker publica solo en `127.0.0.1`, así que el
  driver de Neo4j recibe *connection refused* por IPv6 y recién después prueba IPv4. Funciona, pero el
  mensaje de error de Neo4j siempre incluye ese rechazo: no hay que confundirlo con la causa real.
- **Un puerto interno no publicado da *connection refused*:** `localhost:7199` (JMX de Cassandra).
- **Un puerto abierto puede ser de otro proceso:** `localhost:7000` es el gossip interno de Cassandra,
  pero en la notebook lo ocupa AirPlay (ControlCenter de macOS). El TCP conecta y el driver CQL falla.
- **Un contenedor pausado acepta TCP.** El `docker-proxy` del puerto publicado sigue escuchando: la
  prueba TCP da OK y el protocolo no responde. Por eso la API distingue 503 (rechazada) de 504 (sin
  respuesta), y el diagnóstico no se detiene en la capa TCP.

## Si la API corriera en un contenedor

Solo cambia la configuración, no el código: los hosts pasan a ser los nombres de los servicios
(`mongodb`, `neo4j`, `cassandra`, `redis`, `influxdb`, `iris`) y las pruebas del Hito 11 tendrían que
ejecutarse dentro de ese contenedor para respetar el origen real. Queda como mejora propuesta.
