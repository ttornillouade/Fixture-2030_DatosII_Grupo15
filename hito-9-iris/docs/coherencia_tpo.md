# Coherencia con el TPO

| Hito | Responsabilidad | Relación con el módulo de IRIS |
|---|---|---|
| Hito 4 — MongoDB | Fuente de verdad de `Equipo` y `Jugador` | Mismas identidades: `E001`… y `E001J09`. IRIS no reemplaza la ficha del jugador: guarda lo necesario para validar el partido (dorsal, posición, equipo). |
| Hito 5 — Neo4j | Partidos, sedes y relaciones del fixture | Mismas identidades `P001`, `S01`, fase. Neo4j responde preguntas de recorrido del fixture; IRIS custodia el **acta** de cada partido. |
| Hito 6 — Cassandra | Comentarios masivos | Sin relación directa: IRIS no guarda texto libre. |
| Hito 7 — Redis | Sesiones y caché | Redis puede cachear el marcador en vivo; la fuente es `Partido.Marcador()` en IRIS. |
| Hito 8 — InfluxDB | Estadísticas temporales segundo a segundo | InfluxDB registra la **evolución** (posesión, pases, actividad). IRIS registra los **hechos oficiales** del partido (goles, tarjetas, sustituciones) y su estado. El mismo P001 = E001 vs E002 en S01 aparece en los dos. |

## Regla de arquitectura

> IRIS se usa donde hacen falta reglas de consistencia fuertes sobre un grafo de objetos:
> el partido como máquina de estados, con eventos inalterables y referencias que no pueden
> quedar rotas. Las demás tecnologías conservan sus responsabilidades; entre módulos se
> comparten identificadores, no copias de las entidades.

## Flujo

```text
MongoDB (equipos, jugadores) ──ids──┐
Neo4j (fixture, sedes) ──ids────────┤
                                    ▼
                   IRIS: Partido (PROGRAMADO → EN_JUEGO → FINALIZADO)
                         └── Eventos oficiales (inalterables)
                                    │
                 marcador / acta ───┼──► Redis (caché del marcador en vivo)
                                    └──► consultas SQL para reportes
InfluxDB guarda en paralelo las métricas de alta frecuencia del mismo partido.
```
