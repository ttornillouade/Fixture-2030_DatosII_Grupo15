# Grupo 15 — Hito 7: Caché de Usuarios y Sesiones del Fixture 2030

## 1. Objetivo y alcance

El Hito 7 implementa en Redis el estado temporal de usuarios y una capa de caché para accesos repetidos del Fixture 2030.

Redis no reemplaza los módulos persistentes desarrollados previamente. La decisión central es separar:

```text
fuente de verdad
        ≠
copia temporal / estado transitorio
```

Se implementan tres necesidades:

1. sesiones con expiración por inactividad;
2. caché de una ficha de equipo con cache-aside e invalidación;
3. ranking temporal de partidos mediante una operación concurrente atómica.

## 2. Problema de concurrencia

Millones de usuarios pueden navegar en simultáneo y generar:

- validaciones repetidas de sesión;
- renovaciones de actividad;
- lecturas reiteradas de equipos;
- actualizaciones concurrentes de contadores o rankings temporales.

El objetivo no es persistir nuevamente esos datos de negocio, sino mantener cerca del consumidor aquello que puede vivir temporalmente.

## 3. Patrones de acceso

| Patrón | Entrada | Respuesta | Frecuencia | Redis |
|---|---|---|---|---|
| crear sesión | session_id + user_id | sesión válida | media/alta | Hash + TTL |
| validar sesión | session_id | atributos / ausencia | muy alta | Hash |
| renovar actividad | session_id | TTL renovado | alta | MULTI/EXEC |
| cerrar sesión | session_id | clave eliminada | media | DEL |
| consultar equipo | equipo_id | resumen | muy alta | Hash cacheado |
| cache miss | equipo_id | fuente de verdad + reconstrucción | media/baja | cache-aside |
| invalidar equipo | equipo_id | copia eliminada | baja | DEL |
| ranking temporal | partido_id | score + ranking | alta | Sorted Set |

## 4. Namespace

```text
fixture2030:session:{session_id}
fixture2030:cache:equipo:{equipo_id}
fixture2030:ranking:partidos:consultas:{fecha}
fixture2030:meta:hito
```

La convención permite reconocer dominio, alcance y propósito de cada clave.

## 5. Sesiones

### Estructura

```text
HASH fixture2030:session:{session_id}

session_id
user_id
created_at
last_activity
access_status
locale
```

### TTL

```text
1800 segundos = 30 minutos
```

Se adopta una expiración deslizante por inactividad.

Una actividad autenticada relevante actualiza `last_activity` y renueva el TTL.

### Justificación

Treinta minutos evita conservar indefinidamente una sesión abandonada, pero permite navegar un partido sin autenticaciones demasiado frecuentes.

No se presenta el valor como universal: es una política del Fixture 2030 que puede ajustarse según seguridad y experiencia de usuario.

### Expiración nativa

La clave vence mediante Redis `EXPIRE`.

No se implementa un proceso que recorra todas las sesiones buscando manualmente cuáles vencieron.

### Ausencia

Si la sesión no existe:

```text
vencida / cerrada / inválida
        ->
reautenticación
```

Para sesión se adopta fail-closed: si Redis no puede validar el estado, no se considera autenticado al usuario por defecto.

## 6. Atomicidad de creación y renovación

La demostración de sesión agrupa:

```text
HSET
EXPIRE
```

mediante `MULTI/EXEC`.

El objetivo es evitar un estado intermedio donde exista el Hash sin política temporal.

Esto es distinto de afirmar que cualquier secuencia de comandos Redis es automáticamente atómica: la atomicidad debe introducirse deliberadamente.

## 7. Caché de Equipo

Se cachea un resumen de Equipo:

```text
fixture2030:cache:equipo:E001
```

como `HASH`.

Campos:

```text
id
nombre
pais
confederacion
grupo
```

TTL:

```text
300 segundos
```

### Fuente de verdad

La fuente de verdad permanece en el módulo documental del Hito 4.

El archivo:

```text
data/fuente_verdad_equipos_demo.json
```

es únicamente una respuesta reproducible para el laboratorio, no una nueva base oficial.

## 8. Cache-aside

### HIT

```text
Aplicación -> Redis -> dato -> respuesta
```

### MISS

```text
Aplicación
  -> Redis
  -> MISS
  -> MongoDB / fuente de verdad
  -> respuesta
  -> HSET Redis
  -> EXPIRE 300
```

### Redis no disponible

Para una ficha cacheada se puede degradar a:

```text
aplicación -> fuente de verdad
```

Redis mejora latencia, pero no es indispensable para preservar el dato persistente.

## 9. Invalidación

El TTL no se considera suficiente para coherencia.

Si un equipo cambia en la fuente de verdad:

1. se confirma primero la escritura persistente;
2. se elimina `fixture2030:cache:equipo:{id}`;
3. la siguiente lectura produce cache miss;
4. se reconstruye la copia.

Se elige **invalidate-on-write** en lugar de modificar simultáneamente MongoDB y Redis.

### Trade-off

```text
invalidar
+ menor riesgo de dos valores distintos
- siguiente lectura paga un MISS
```

Es preferible un MISS controlado a servir una copia que se creyó actualizada pero quedó parcialmente sincronizada.

## 10. Operación concurrente y ranking

Se utiliza un `SORTED SET`:

```text
fixture2030:ranking:partidos:consultas:{fecha}
```

Cada miembro es:

```text
P001
P002
...
```

y el score representa actividad/consultas temporales.

Actualización:

```redis
ZINCRBY clave 1 P001
```

Lectura:

```redis
ZREVRANGE clave 0 9 WITHSCORES
```

### Atomicidad

`ZINCRBY` es un comando Redis único.

No se implementa:

```text
GET score
score = score + 1
SET score
```

porque dos clientes podrían leer el mismo valor y perder una actualización.

La prueba concurrente ejecuta múltiples clientes sobre `ZINCRBY` y verifica que el score final coincida con la cantidad de incrementos.

## 11. Ciclo de vida del ranking

TTL:

```text
172800 segundos = 48 horas
```

El ranking es temporal. No se conserva indefinidamente ni se utiliza como fuente histórica.

Si el negocio requiriera análisis histórico de popularidad, correspondería persistir eventos o agregados en otro módulo.

## 12. Política de memoria

Configuración local:

```text
maxmemory 256mb
maxmemory-policy noeviction
```

### Motivo

Una política global de LRU podría expulsar una sesión válida por presión generada por el caché.

Con `noeviction` Redis no elimina arbitrariamente sesiones activas.

### Costo

Cuando se alcanza el límite, nuevas escrituras que requieren memoria pueden fallar.

La aplicación debe manejarlo:

- caché: continuar desde la fuente de verdad;
- sesión: no considerar exitosa una creación/renovación que Redis rechazó;
- operación: registrar y alertar presión de memoria.

### TTL no es evicción

TTL:

```text
el dato dejó de ser válido por tiempo
```

Evicción:

```text
Redis necesita liberar memoria
```

Son problemas distintos.

En esta configuración las claves siguen venciendo por TTL aunque `maxmemory-policy` sea `noeviction`.

## 13. Persistencia local

El laboratorio monta:

```text
~/docker/data/redis
```

y habilita AOF:

```text
appendonly yes
appendfsync everysec
```

Esto permite conservar el estado local entre reinicios del contenedor.

La persistencia no transforma a Redis en fuente de verdad de Equipos.

## 14. Nodo local vs producción

La práctica utiliza un único nodo.

No se presenta como:

```text
alta disponibilidad
Redis Cluster
Sentinel
replicación multirregional
```

En producción sería razonable separar sesiones y caché para aplicar políticas de memoria y disponibilidad diferentes.

## 15. Datos reproducibles

La carga de muestra crea:

- 12 sesiones;
- TTL de 30 minutos;
- ranking temporal;
- fuente de verdad simulada para 8 equipos.

Los mismos IDs pueden recargarse sin crear nuevas entidades lógicas.

## 16. Inspección segura

No se utiliza:

```text
KEYS *
```

como operación normal.

La inspección se realiza con:

```redis
SCAN 0 MATCH fixture2030:* COUNT 100
```

y la limpieza usa `SCAN` + `UNLINK`.

## 17. Scripts

```text
inicializacion.redis
    -> metadatos del módulo

carga_muestra.redis
    -> sesiones y ranking reproducibles

sesiones.redis
    -> alta, lectura, renovación y cierre

cache.redis
    -> operaciones Redis básicas sobre cache

cache_aside.py
    -> HIT/MISS e invalidación con fuente externa demo

concurrencia.redis
    -> sorted set básico

prueba_concurrencia.sh
    -> clientes concurrentes + ZINCRBY

metricas.redis
    -> server, memory, stats, SCAN

prueba_rendimiento.sh
    -> benchmark reproducible

generar_evidencia.sh
    -> evidencia funcional completa
```

## 18. Prueba de rendimiento

La prueba se ejecutó el **27/09/2026 a las 23:43:01 (-03)** con Redis **8.10.2**, utilizando 50.000 operaciones por prueba y 50 clientes concurrentes.

| Operación | Throughput | p50 |
|---|---:|---:|
| `SET` con TTL de 300 s | 118.764,84 req/s | 0,335 ms |
| `GET` | 149.253,73 req/s | 0,175 ms |
| `HSET` de sesión | 105.708,25 req/s | 0,359 ms |

Durante la medición, `docker stats` informó 0,27 % de CPU y 7,652 MiB de memoria para el contenedor en el instante observado. Redis informó `used_memory_human=11.80M`, un pico de 12,66 MiB y `maxmemory=256 MiB` con política `noeviction`.

`docker stats` e `INFO memory` no representan exactamente la misma métrica de memoria, por lo que se registran por separado.

La prueba se realizó en un nodo único local mediante Docker y `redis-benchmark`. Estos valores se conservan como evidencia reproducible del laboratorio y no como estimación de capacidad productiva. La medición registra p50, pero no p95/p99, failover, red real ni presión efectiva de `maxmemory`.

## 19. Evidencia

La evidencia funcional se genera con:

```bash
bash scripts/generar_evidencia.sh
```

Incluye:

- versión;
- `PING`;
- política de memoria;
- sesión CRUD;
- TTL;
- vencimiento observado;
- cache MISS;
- cache HIT;
- invalidación;
- reconstrucción;
- concurrencia;
- ranking;
- métricas.

Los resultados deberán provenir de la ejecución real en la notebook del grupo.

## 20. Coherencia con los Hitos 1–6

### MongoDB

Fuente de verdad de Equipo/Jugador.

### Neo4j

Relaciones deportivas y partidos. Los `P001...` del ranking mantienen la misma identidad semántica.

### Cassandra

Comentarios masivos. Redis no duplica ese módulo.

### Redis

Estado de sesión, caché reconstruible y estructuras temporales.

La arquitectura conserva la separación de responsabilidades trabajada a partir de la devolución del Hito 4.

## 21. Trade-offs

| Decisión | Beneficio | Costo |
|---|---|---|
| Hash para sesión | acceso directo por ID | no resuelve búsquedas arbitrarias |
| TTL 30 min deslizante | libera sesiones inactivas | renovaciones generan escrituras |
| caché de Equipo | menor latencia repetida | posible obsolescencia temporal |
| invalidate-on-write | coherencia simple | próximo acceso es MISS |
| TTL 5 min caché | limita antigüedad | no reemplaza invalidación |
| ZINCRBY | incremento concurrente atómico | ranking solo temporal |
| noeviction | evita expulsión silenciosa de sesión | escrituras pueden fallar al llenar memoria |
| nodo único | laboratorio simple | sin HA |
| AOF local | recuperación entre reinicios | más I/O |

## 22. Estado final de ejecución

- [x] Redis ejecutado con `redis:latest`.
- [x] Redis observado: versión 8.10.2.
- [x] `PING` respondido correctamente.
- [x] carga inicial reproducible ejecutada.
- [x] CRUD de sesión ejecutado.
- [x] TTL de 1800 segundos verificado.
- [x] renovación deslizante del TTL verificada.
- [x] expiración automática demostrada.
- [x] flujo cache MISS → fuente de verdad demo → HIT ejecutado.
- [x] invalidación y reconstrucción ejecutadas.
- [x] prueba concurrente con `ZINCRBY` ejecutada sin pérdida de incrementos.
- [x] ranking temporal verificado.
- [x] evidencia funcional generada localmente.
- [x] benchmark ejecutado.
- [x] recursos y memoria registrados.
- [x] resultados reales incorporados a la documentación.

La evidencia de rendimiento se conserva en `docs/evidencia/rendimiento_hito7_20260927_234301.txt`.

---

# Anexo A — Requisitos funcionales

| RF | Respuesta |
|---|---|
| RF1 | Docker Compose + `redis-cli` |
| RF2 | patrones documentados |
| RF3 | CRUD de sesión |
| RF4 | expiración deslizante 1800 s |
| RF5 | atributos del Hash de sesión |
| RF6 | caché de Equipo |
| RF7 | cache-aside + invalidación |
| RF8 | `ZINCRBY` concurrente |
| RF9 | Sorted Set |
| RF10 | `noeviction` + 256 MB |
| RF11 | dataset reproducible |
| RF12 | benchmark real ejecutado y documentado |
| RF13 | script de evidencia + resultados reales |

# Anexo B — Requisitos no funcionales

| RNF | Respuesta |
|---|---|
| RNF1 | `redis:latest` |
| RNF2 | `~/docker/data/redis` |
| RNF3 | README y scripts |
| RNF4 | estructuras vinculadas a operaciones |
| RNF5 | namespace explícito |
| RNF6 | ciclo de vida documentado |
| RNF7 | sin secretos |
| RNF8 | SCAN en lugar de búsqueda global bloqueante |
| RNF9 | scripts separados |
| RNF10 | evidencia real con fecha, versión, recursos y resultados |
