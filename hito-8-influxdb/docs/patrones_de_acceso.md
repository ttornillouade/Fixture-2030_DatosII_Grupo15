# Patrones de acceso — Hito 8

Se definieron **antes** que tablas, tags y fields. Cada decisión del modelo se justifica con uno o más patrones (RNF4).

| ID | Quién genera / consulta | Rango temporal | Dimensiones (filtro / segmentación) | Medidas | Frecuencia de llegada | Precisión | Ausencia, retraso o dato tardío |
|---|---|---|---|---|---|---|---|
| PA1 Estado en vivo | App, TV, pantallas del estadio | últimos 1–2 min o último valor | partido_id, equipo_id | posesión, pases, tiros, goles | 1 pt/s por equipo; consultas de cientos por segundo | segundo (se guarda ms) | Sin puntos recientes → mostrar último valor (LVC) con "sin actualización desde hh:mm:ss". Nunca 0. |
| PA2 Ventana de un partido | Analistas, periodistas | minuto X a Y (5–15 min) | partido_id (+ equipo_id) | todas las del equipo | a demanda | segundo | Entretiempo/cortes: los minutos sin puntos se muestran como NULL (gapfill), no como 0. |
| PA3 Comparar equipos | App, analistas | partido completo en bloques de 5–15 min | partido_id, equipo_id / condicion | pases, tiros (acumulados), posesión | a demanda | minuto | Si falta un bloque, la diferencia se calcula contra el último bloque disponible. |
| PA4 Rendimiento de un jugador | Cuerpo técnico | últimos 5–15 min y partido completo | partido_id, equipo_id, jugador_id | velocidad (avg/max), distancia, sprints | 1 pt/s por jugador | segundo | Jugador sustituido: deja de tener puntos (fin de la serie), no se rellena. |
| PA5 Eventos del partido | App (relato), analistas | partido completo | partido_id, equipo_id, tipo_evento | ocurrencias, éxito, xG | irregular; ráfagas | milisegundo (orden entre eventos) | Evento tardío (llega minutos después): se acepta con su timestamp original y aparece en su lugar en la línea de tiempo. |
| PA6 Monitoreo operativo | Equipo de operaciones (SRE) | partido en curso, bloques de 1–10 min | partido_id, plataforma | usuarios activos, solicitudes, errores, latencia p95 | 1 pt/s por plataforma | segundo | Sin puntos de una plataforma = alerta (la fuente o el backend cayó). |
| PA7 Comparar audiencia entre sedes/fases | Negocio | todo el torneo | pais_sede, fase, partido_id | pico y promedio de usuarios simultáneos | a demanda | segundo → minuto | Partidos sin datos no aparecen; no se imputan. |
| PA8 Análisis histórico | Analistas, negocio | días a semanas | partido_id, equipo_id, jugador_id, plataforma | resúmenes de 1 min | después del partido | minuto | Se lee la base histórica; el detalle por segundo ya expiró. |
| PA9 Verificación de carga | Equipo de datos | por partido | partido_id + clave de serie | conteos y tipos | después de cada carga | — | Diferencias contra el manifiesto = carga incompleta o duplicada. |

## Relación patrón → elementos del modelo

| Patrón | Tabla | Tags que usa | Consulta del repositorio |
|---|---|---|---|
| PA1 | estadisticas_equipo, actividad_usuarios | partido_id, equipo_id, plataforma | c06, c07 (+ `caches_ultimo_valor.sh`) |
| PA2 | estadisticas_equipo | partido_id, equipo_id | c01, c08 |
| PA3 | estadisticas_equipo | partido_id, equipo_id, condicion | c03, a01, a02 |
| PA4 | rendimiento_jugador | partido_id, equipo_id, jugador_id | c02, a04 |
| PA5 | eventos_partido | partido_id, equipo_id, tipo_evento | c09, a03, a06 |
| PA6 | actividad_usuarios | partido_id, plataforma | c04, a05, a06 |
| PA7 | actividad_usuarios | pais_sede, fase, partido_id | c05 |
| PA8 | *_1m (histórico) | los mismos que la tabla original | a07 |
| PA9 | todas | clave de serie | `validacion.py` |
