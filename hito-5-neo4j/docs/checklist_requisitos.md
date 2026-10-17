# Checklist de requisitos — Hito 5

| Requisito | Evidencia dentro del módulo |
|---|---|
| RF1 | `docker-compose.yml` + README |
| RF2 | `docs/modelo_grafo.md` |
| RF3 | `Equipo`, `Jugador`, `Partido`, `Evento`, `Sede` |
| RF4 | `PERTENECE_A`, `DISPUTA`, `SE_JUEGA_EN`, `OCURRE_EN` |
| RF5 | IDs `E001`, `E001-J01`, etc. |
| RF6 | 64 equipos, 1.536 jugadores, 127 partidos, 6 sedes, 508 eventos |
| RF7 | `queries/crud.cypher` |
| RF8 | `queries/consultas_grafo.cypher` |
| RF9 | `queries/analisis_relacional.cypher` |
| RF10 | `queries/estructura.cypher` y `queries/rendimiento.cypher` |
| RF11 | `scripts/generar_evidencia.sh` + capturas reales |
| RNF1 | `neo4j:latest` |
| RNF2 | volúmenes `neo4j_data`, `neo4j_logs` |
| RNF3 | README + scripts |
| RNF4 | `MERGE` + segunda carga |
| RNF5 | consultas separadas por propósito |
| RNF6 | `docs/modelo_grafo.md` y `docs/decisiones.md` |
| RNF7 | consultas + controles de integridad |
| RNF8 | `.env.example` |
