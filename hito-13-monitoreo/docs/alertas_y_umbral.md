# Alertas y umbrales operativos (RF9, 5.4)

Las reglas están en `prometheus/reglas-o-alertas.yml` y se ven en Prometheus → *Alerts*. En el laboratorio
no hay Alertmanager: una alerta `firing` se ve en Prometheus y en Grafana, pero no notifica a nadie. La
notificación (canal de guardia, mail) queda propuesta.

Los umbrales son **experimentales**: salen de lo medido en el Hito 12 en una notebook, no de un acuerdo de
nivel de servicio con la FIFA. Se indican así para no presentarlos como objetivos validados.

## BaseNoDisponible

| | |
|---|---|
| Métrica | `fixture2030_dependencia_up` (ping de la API a cada base, cada 15 s) |
| Condición | `== 0` |
| Duración mínima | 30 s (dos pings fallidos seguidos: evita alertar por un timeout aislado) |
| Severidad | crítica |
| Componente | la base indicada en la etiqueta `base` |
| Impacto en el Fixture | Los endpoints de esa base responden 503 o 504. **El resto sigue funcionando** (cada endpoint usa una sola base). Por ejemplo, con Cassandra caída no se pueden leer ni publicar comentarios, pero las fichas de equipos (MongoDB) y las sesiones (Redis) siguen respondiendo |
| Quién atiende | guardia de datos |
| Acción | 1) `docker ps` y `docker logs fixture2030-<base>`; 2) si la sonda TCP también falla, la base o el contenedor están caídos → reiniciar (`docker start`); 3) si la sonda TCP responde, revisar credenciales/contexto (Hito 11) |
| Por qué el umbral | 30 s es lo mínimo para descartar un ping lento aislado y es corto frente a un partido (90 min): perder comentarios durante más de medio minuto ya es visible para los usuarios |

## SondaTCPFallando

| | |
|---|---|
| Métrica | `probe_success{job="sonda_tcp"}` |
| Condición | `== 0` durante 30 s |
| Severidad | crítica |
| Impacto | Confirma, desde fuera de la API, que el puerto de la base no acepta conexiones |
| Acción | Igual que la anterior. Si esta alerta **no** está activa pero `BaseNoDisponible` sí, el problema no es el contenedor sino el acceso (driver, credenciales, base pausada) |
| Por qué | Dos señales independientes evitan culpar a la base por un error de la API, y viceversa |

## ErroresServidorAltos

| | |
|---|---|
| Métrica | regla `fixture2030:api_errores_5xx:ratio1m` (proporción de 5xx por base) |
| Condición | `> 0.02` **y** más de 1 req/s |
| Duración mínima | 1 min |
| Severidad | alta |
| Impacto | Usuarios que no pueden leer o publicar |
| Quién atiende | desarrollo de la API |
| Acción | Separar 503 de 504 en el panel *Respuestas no exitosas*: 503 = rechazo (base caída), 504 = la base acepta pero no responde en 3 s (saturada o pausada) |
| Por qué el umbral | En todas las corridas válidas del Hito 12 la tasa de 5xx fue 0 %; 2 % sostenido durante un minuto ya no es ruido. El mínimo de 1 req/s evita alertar cuando hay 1 error en 3 requests de madrugada |

## LatenciaComentariosAlta

| | |
|---|---|
| Métrica | regla `fixture2030:api_latencia_p95:1m{fuente="Cassandra"}` |
| Condición | `> 0.3` s |
| Duración mínima | 2 min |
| Severidad | media |
| Impacto | El feed en vivo se siente lento; si sigue creciendo, aparecen los 504 (TIMEOUT_S = 3 s) |
| Acción | Comparar CPU de la API con la de Cassandra (Hito 12): si la API está en 100 % de un núcleo, escalar procesos; si es Cassandra, revisar la caché (tasa de aciertos) y la compactación |
| Por qué el umbral | En la línea base del Hito 12 (60 usuarios, API saturada) la latencia del servidor para lecturas tuvo p95 de ~300 ms; con la optimización bajó muy por debajo. 300 ms durante 2 minutos indica que se volvió a la zona de saturación |

## TargetDeMonitoreoCaido

| | |
|---|---|
| Métrica | `up{job=~"api|redis|mongodb"}` |
| Condición | `== 0` durante 1 min |
| Severidad | baja |
| Impacto | Se pierde visibilidad, no necesariamente servicio |
| Acción | `verificar_targets.py`: el `lastError` dice si es red, puerto o exporter |
| Por qué | Sin esta alerta, un panel vacío se puede confundir con "no hay tráfico" |

## Qué decisión habilita cada alerta

| Alerta | Decisión |
|---|---|
| BaseNoDisponible + SondaTCPFallando | Reiniciar o conmutar la base; comunicar degradación parcial (solo ese módulo) |
| Solo BaseNoDisponible | Revisar configuración/credenciales; no reiniciar la base |
| ErroresServidorAltos con 504 | Hay saturación: reducir carga (caché, límite), escalar |
| LatenciaComentariosAlta sin errores | Escalar antes de que haya errores (procesos de la API, réplicas) |
