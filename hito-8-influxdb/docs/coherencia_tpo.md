# Coherencia con el TPO

| Hito | Responsabilidad | Relación con el módulo temporal |
|---|---|---|
| Hitos 1–3 | Selección de tecnologías y arquitectura distribuida | InfluxDB se incorpora para observaciones de alta frecuencia indexadas por tiempo, que no encajan como documentos, grafos ni claves con TTL. |
| Hito 4 — MongoDB | Fuente de verdad de `Equipo` y `Jugador` | `equipo_id` (E001..E048) y `jugador_id` (`E001J09`) son las mismas identidades. InfluxDB no guarda nombres ni fichas, solo ids como tags. |
| Hito 5 — Neo4j | `Partido`, sedes, relaciones del fixture | `partido_id` (P001..P104), `sede_id` y `fase` son las mismas identidades del grafo. |
| Hito 6 — Cassandra | Comentarios masivos | No se guardan textos en InfluxDB: el texto libre tiene cardinalidad ilimitada y otra forma de consulta. |
| Hito 7 — Redis | Sesiones y caché | Redis tiene el estado actual de cada sesión; InfluxDB guarda la **evolución** agregada (`usuarios_activos` por plataforma y segundo) sin user_id ni session_id. |

## Regla de arquitectura

> Cada tecnología conserva la responsabilidad para la cual fue seleccionada. InfluxDB guarda
> la evolución temporal de medidas; las entidades viven en sus fuentes de verdad y solo se
> referencian por id.

## Flujo

```text
Proveedor / tracking ──► InfluxDB (vivo) ──► app / pantallas (último valor, ventanas)
                                │
Backend (sesiones Redis) ──► actividad_usuarios
                                │
                         downsampling 1 min
                                ▼
                       InfluxDB (histórico) ──► análisis del torneo
MongoDB (equipos/jugadores) y Neo4j (partidos/sedes) aportan los nombres al presentar resultados.
```
