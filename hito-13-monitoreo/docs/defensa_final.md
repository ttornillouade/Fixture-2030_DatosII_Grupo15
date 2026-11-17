# Defensa final: síntesis (RF13-RF16)

## Respuesta a la pregunta central

> ¿Por qué esta combinación de modelos, estructuras, estrategias de distribución y mecanismos de
> observabilidad resulta adecuada para el Fixture Mundial 2030 bajo las condiciones planteadas?

1. **Porque cada tipo de dato tiene su patrón de acceso y su base**: catálogo de equipos (documental),
   relaciones entre jugadores, partidos y rivales (grafo), comentarios masivos por partido (columnar con
   partición por ventana y shard), sesiones con vencimiento (clave-valor en memoria), mediciones por segundo
   (series temporales) y el partido como entidad con reglas de estado (multimodelo con objetos y SQL).
   Una sola base haría bien uno o dos de estos accesos y mal los demás (`decisiones_de_arquitectura.md`).
2. **Porque las fallas quedan aisladas**: cada endpoint usa una sola base, con el mismo contrato de error
   (503/504) y el mismo límite de tiempo (3 s). **Medido**: con Cassandra detenida, solo fallaron los
   comentarios; MongoDB y Redis siguieron respondiendo, y la API se recuperó sola al volver la base.
3. **Porque la consistencia se elige por módulo, no para todo el sistema**: disponibilidad para comentarios,
   sesiones y estadísticas; consistencia fuerte para el estado del partido.
4. **Porque se puede observar y medir**: Prometheus y Grafana muestran disponibilidad, latencia, volumen y
   errores por base; la prueba de carga del Hito 12 encontró el cuello de botella real (la API, no la base),
   lo corrigió y lo verificó con la misma carga y validación de integridad.

**Con estas condiciones**: es un laboratorio de un nodo por base en una PC. La replicación, la distribución
geográfica y el volumen del torneo completo son diseño y estimación, no medición (`limitaciones_y_evidencia.md`).

## Mapa de evidencia para responder "¿cómo lo demuestran?" (RF16)

| Afirmación | Cómo se demuestra en el momento | Archivo |
|---|---|---|
| Cada base resuelve un acceso distinto | Requests de Swagger por base (demo, pasos 2-4) | `defensa/demo.md` |
| La partición de Cassandra evita escanear | `cqlsh`: `DESCRIBE TABLE fixture2030_comments.comentarios_por_partido` y la consulta del adaptador con clave completa | `hito-10-api/app/adaptadores/cassandra.py` |
| El grafo resuelve recorridos | `GET /jugadores/E001-J09/partidos` y la consulta Cypher del adaptador | `hito-10-api/app/adaptadores/neo4j_grafo.py` |
| Las sesiones vencen solas | `redis-cli TTL fixture2030:session:s-demo-001` | Hito 7 |
| El estado del partido es consistente | `PATCH /partidos/P128/estado` → 409 al saltear un estado | Hito 9/10 |
| Una base caída no tira la plataforma | Prueba de falla (en vivo o guardada) | `evidencia/prueba_de_falla_cassandra_*` |
| El cuello de botella era la API | CPU por componente y latencia cliente vs servidor | `hito-12-carga-optimizacion/docs/linea_base.md` |
| La optimización funcionó y no rompió datos | Tabla antes/después con 3 repeticiones, integridad OK | `hito-12-carga-optimizacion/docs/evidencia/comparacion.md` |
| Las métricas son reales | Targets UP y consultas PromQL | `evidencia/prometheus_targets.json`, `docs/metricas_y_consultas.md` |

## Trade-offs aceptados

| Decisión | Beneficio | Costo aceptado |
|---|---|---|
| Seis productos | Cada patrón de acceso en la base adecuada | Seis cosas que operar, respaldar y monitorear |
| Comentarios en dos tablas (Cassandra) | Lectura por partido y por usuario sin escaneos | Duplicación; batch para mantenerlas juntas |
| 8 shards por ventana | Reparte escrituras de un partido caliente | La lectura son 8 consultas + fusión (fue el costo dominante en la carga) |
| Caché del feed (TTL 1 s) | Más throughput y menos latencia mediana (Hito 12) | El feed puede llegar hasta 1 s desactualizado; más memoria en Redis |
| Varios procesos de la API | Usa más núcleos | Más memoria; métricas en modo multiproceso |
| `noeviction` en Redis | No se pierden sesiones en silencio | Al llenarse, se rechazan sesiones nuevas (alerta y panel de memoria) |
| Un endpoint, una base | Fallas aisladas, latencia predecible | Las preguntas que cruzan fuentes necesitan un Data Mart (ETL, retraso) |

## Qué mejoraríamos en una siguiente iteración

1. Réplicas reales (replica set de MongoDB, Cassandra con RF=3, réplica de Redis) y repetir la prueba de falla
   con caída de **un nodo** en lugar de la base entera.
2. Métricas internas de Cassandra (JMX exporter) y CPU por contenedor (cAdvisor) en Prometheus.
3. Alertmanager con un canal de guardia.
4. API detrás de un balanceador con varias instancias; caché en otros endpoints calientes.
5. Programar el ETL del Data Mart (cada 5 minutos, con marca de agua) y sumar eventos de IRIS y
   estadísticas de InfluxDB a la proyección.
