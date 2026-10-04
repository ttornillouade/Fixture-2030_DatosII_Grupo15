# Consultas y agregaciones

Todas las consultas están en `sql/` y se ejecutan con `scripts/consultar.py`, que reemplaza
`{{PARTIDO}}`, `{{VENTANA_DESDE}}`, etc. con valores del manifiesto e informa el tiempo de
respuesta. **Todas acotan rango temporal** y, cuando corresponde, partido/equipo/jugador (RNF8).
El partido de referencia es el primero de la corrida que tiene goles.

## Consultas (RF8)

| Archivo | Demuestra | Patrón | Resultado esperado / interpretación | Límites |
|---|---|---|---|---|
| c01_ventana_partido | ventana temporal | PA2 | 600 filas (2 equipos x 300 s) entre los minutos 60 y 65; los contadores solo crecen | Devuelve datos crudos: para ventanas largas usar c03 |
| c02_filtro_jugador | filtro por 3 tags | PA4 | 10 bloques de 30 s con 30 muestras cada uno | Si el jugador fue sustituido, faltan bloques |
| c03_comparacion_equipos | comparación de dos dimensiones | PA3 | local vs visitante cada 5 min; el entretiempo no aparece | La posesión es acumulada: el avg del bloque se mueve lento |
| c04_comparacion_plataformas | comparación de fuentes | PA6 | pico y promedio de usuarios, solicitudes, tasa de error y latencia por plataforma | La tasa de error es sobre el partido completo |
| c05_comparacion_sedes | comparación entre partidos | PA7 | pico de usuarios simultáneos por país sede y fase | Recorre todo el rango de la corrida: con el perfil torneo conviene usar el histórico |
| c06_ventana_reciente | ventana con `now()` | PA1 | filas solo si corre `simulador_vivo.py`; el corte de la fuente se ve como un hueco | Sin fuente activa = sin filas (respuesta esperada) |
| c07_ultimo_valor_cache | Last Value Cache | PA1 | un registro por (partido, equipo) con el último valor | Requiere `caches_ultimo_valor.sh` |
| c08_ausencia_entretiempo | ausencia de puntos | PA2 | `date_bin_gapfill` + `locf`: minutos del entretiempo con muestras NULL y posesión arrastrada | `gapfill` exige rango temporal en el WHERE |
| c09_linea_de_tiempo_goles | eventos irregulares | PA5 | tiros y goles ordenados por ms con autor (field) y xG | — |

## Agregaciones (RF9) y justificación de la función

| Archivo | Medida | Tipo semántico | Función | Por qué no otra |
|---|---|---|---|---|
| a01_posesion_por_bloque | posesion_pct | porcentaje acumulado (gauge) | `avg` del bloque y `last_value` al cierre | sumar porcentajes no tiene significado |
| a02_pases_por_intervalo | pases_intentados | contador acumulado | `max` por bloque y `max - lag(max)` | `sum` del contador sumaría el mismo pase cientos de veces |
| a03_eventos_por_tipo | eventos | ocurrencias | `count(*)` / `sum(valor)`; efectividad = exitosos / total | `avg` de eventos no responde "cuántos" |
| a04_top_distancia | distancia_m / velocidad_kmh | contador / gauge | `max` (distancia total), `avg` y `max` (velocidad) | sumar velocidades no da distancia |
| a05_actividad_resumen | solicitudes / usuarios / latencia p95 | delta / gauge / percentil | `sum` / `avg`+`max` / `max` | promediar p95 no da el p95 del período; sumar usuarios en el tiempo cuenta la misma persona muchas veces |
| a06_impacto_goles_en_trafico | solicitudes + goles | delta + evento | `sum`/60 por minuto cruzado con `count` de goles | — |
| a07_historico_1m | resúmenes de 1 min | según la tabla original | `avg` de promedios de igual peso (todos los minutos tienen 60 muestras), `max` de contadores | si los minutos tuvieran distinta cantidad de muestras habría que ponderar por `muestras` |

## Interpretación en el contexto del partido

- **a06** ordena los minutos por solicitudes/s: el minuto del gol aparece primero (en la corrida demo con semilla 2030, ~90 % más tráfico que un minuto típico) y decaimiento en los minutos siguientes. La capacidad debe planificarse para esos picos y no para el promedio.
- **a02** muestra el ritmo de juego (pases cada 5 min) y permite ver qué equipo domina cada tramo aunque la posesión acumulada cambie poco.
- **a04**: los titulares recorren ~11 km; los que entran desde el banco, menos, porque tienen menos minutos (menos puntos, no menos rendimiento).
- **c05**: compara audiencias simultáneas entre sedes y fases; los partidos de eliminación tienen mayor base de audiencia.

Los valores concretos de cada corrida quedan en `docs/evidencia/evidencia_hito8_*.txt`.
