# Grupo 15 — Hito 8: Series temporales de estadísticas en vivo del Fixture 2030

## 1. Objetivo y alcance

El Hito 8 implementa en InfluxDB 3 (imagen `influxdb:3-core`) el módulo que registra y
recupera estadísticas que cambian segundo a segundo durante los partidos: estadísticas de
equipo, rendimiento físico de jugadores, eventos y actividad de la plataforma.

No reemplaza a los módulos anteriores: las entidades (equipos, jugadores, partidos, sedes)
siguen en sus fuentes de verdad y aquí solo se referencian por id.

```text
entidad / estado actual  (MongoDB, Neo4j, Redis)
            ≠
evolución de una medida en el tiempo  (InfluxDB)
```

## 2. Problema temporal

~166 mil puntos por partido, 104 partidos → **17,3 M puntos** (objetivo 10M+).
Detalle en [docs/problema_temporal.md](docs/problema_temporal.md).

## 3. Patrones de acceso

| Patrón | Rango | Dimensiones | Medidas |
|---|---|---|---|
| PA1 Estado en vivo | últimos 2 min / último valor | partido, equipo | posesión, pases, tiros, goles |
| PA2 Ventana de un partido | minuto X a Y | partido, equipo | todas |
| PA3 Comparar equipos | partido en bloques | partido, equipo, condición | pases, tiros, posesión |
| PA4 Rendimiento de jugador | 5–15 min / partido | partido, equipo, jugador | velocidad, distancia, sprints |
| PA5 Eventos | partido | partido, equipo, tipo | ocurrencias, éxito, xG |
| PA6 Monitoreo operativo | partido en bloques | partido, plataforma | usuarios, solicitudes, errores, latencia |
| PA7 Audiencia por sede | torneo | país sede, fase | pico y promedio de usuarios |
| PA8 Histórico | días/semanas | idem | resúmenes de 1 min |

Detalle (frecuencia, precisión, ausencia y datos tardíos): [docs/patrones_de_acceso.md](docs/patrones_de_acceso.md).

## 4. Modelo multidimensional

```text
estadisticas_equipo  tags: partido_id, equipo_id, condicion, fase, sede_id, pais_sede
                     fields: minuto i, posesion_pct f, pases_intentados i, pases_completados i,
                             tiros i, tiros_al_arco i, recuperaciones i, faltas i, corners i,
                             goles i, xg_acum f
rendimiento_jugador  tags: partido_id, equipo_id, jugador_id
                     fields: minuto i, velocidad_kmh f, distancia_m f, sprints i
eventos_partido      tags: partido_id, equipo_id, tipo_evento
                     fields: jugador_id s, minuto i, exitoso b, x f, y f, xg f, valor i
actividad_usuarios   tags: partido_id, plataforma, fase, pais_sede
                     fields: usuarios_activos i, solicitudes i, errores i, latencia_p95_ms f
time: milisegundos
```

Detalle: [docs/modelo_multidimensional.md](docs/modelo_multidimensional.md).

## 5. Cardinalidad

4.937 series para el torneo. `jugador_id` es tag solo donde hay un patrón que lo filtra
(PA4) y su variación está acotada; en eventos es field. user_id, session_id, ids de evento,
minuto y valores continuos nunca son tags.
Detalle: [docs/cardinalidad_y_escalabilidad.md](docs/cardinalidad_y_escalabilidad.md).

## 6. Carga

Generación determinística → archivos `.lp.gz` + manifiesto → carga HTTP en lotes de 5.000
líneas con 4 hilos, reintentos con backoff, rechazo parcial registrado → validación contra
el manifiesto. Detalle: [docs/carga_de_datos.md](docs/carga_de_datos.md).

## 7. Consultas y agregaciones

9 consultas (ventana, filtros, comparaciones, `now()`, Last Value Cache, gapfill, eventos) y
7 agregaciones con la función elegida según la semántica de la medida.
Detalle: [docs/consultas_y_agregaciones.md](docs/consultas_y_agregaciones.md).

## 8. Retención y granularidad

```text
fixture2030_vivo        14d    1 Hz / ms
fixture2030_historico   none   1 minuto (≈60x menos puntos)
```

Detalle: [docs/retencion_y_granularidad.md](docs/retencion_y_granularidad.md).

## 9. Seguridad local

Token creado en el contenedor, guardado solo en `.env` (ignorado), enmascarado en toda la
evidencia. Detalle: [docs/seguridad_local.md](docs/seguridad_local.md).

## 10. Pruebas y evidencia

[docs/pruebas_y_evidencia.md](docs/pruebas_y_evidencia.md) y [docs/evidencia/](docs/evidencia/).

## 11. Coherencia con el TPO

[docs/coherencia_tpo.md](docs/coherencia_tpo.md).

## 12. Checklist

[docs/checklist_requisitos.md](docs/checklist_requisitos.md).
