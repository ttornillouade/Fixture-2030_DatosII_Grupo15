# Retención y granularidad

## Ciclo de vida

```text
proveedor / tracking / backend
        │  1 Hz y eventos (ms)
        ▼
fixture2030_vivo        retención 14d    precisión original
        │  downsampling.py (cada minuto cerrado en producción; a demanda en el laboratorio)
        ▼
fixture2030_historico   retención none   resúmenes de 1 minuto
```

| Pregunta | Decisión | Justificación |
|---|---|---|
| ¿Cuánto tiempo se necesita la precisión original? | **14 días** | Cubre el partido, el análisis post-partido y la preparación del rival de la ronda siguiente (entre partidos del mismo equipo hay 4–5 días). Más allá, nadie consulta el segundo exacto. |
| ¿Qué se puede resumir? | Todo lo de 1 Hz: estadísticas, rendimiento, actividad. Los eventos se resumen en conteos por minuto y tipo. | Las preguntas históricas (PA8) son por bloques de minutos o por partido. |
| ¿Cuándo expira? | El servidor elimina del vivo los datos más viejos que 14 días (`--retention-period 14d`). El histórico no vence (`none`). | El histórico es ~60 veces más chico y conserva el valor de negocio. |
| ¿Qué granularidad tiene el histórico? | 1 minuto | Permite reconstruir la evolución del partido (90+ puntos por serie) sin el costo del segundo. |

## Agregación por medida

| Tabla original | Medida | En `*_1m` | Motivo |
|---|---|---|---|
| estadisticas_equipo | posesion_pct | `avg` | porcentaje (gauge) |
| | pases, tiros, goles, recuperaciones | `max` | contador acumulado: el máximo del minuto es el valor al cierre |
| | xg_acum | `max` | acumulado |
| rendimiento_jugador | velocidad_kmh | `avg` y `max` | gauge: ritmo y pico |
| | distancia_m, sprints | `max` | acumulados |
| eventos_partido | ocurrencias | `count`, `sum(exitoso)`, `sum(xg)` | eventos |
| actividad_usuarios | usuarios_activos | `avg` y `max` | gauge |
| | solicitudes, errores | `sum` | deltas |
| | latencia_p95_ms | `max` | percentil: el máximo es una cota conservadora |
| todas | muestras | `count(*)` | permite ponderar y detectar minutos incompletos |

Los eventos crudos son pocos (~140 mil en el torneo). Si el negocio pidiera conservar la línea de
tiempo exacta de goles y tarjetas más de 14 días, conviene copiarlos al histórico sin resumir, o
tomarlos de la fuente transaccional del TPO.

## Efecto de cada política

| Política | Consultas en vivo | Análisis histórico | Almacenamiento | Costo |
|---|---|---|---|---|
| Vivo 14d a 1 Hz | Latencia baja sobre datos recientes; LVC para el último valor | Detalle por segundo solo 14 días | Acotado: lo que llega en 14 días (máx. ~17 M puntos si todo el torneo entrara en la ventana) | Fijo y predecible |
| Histórico 1 min sin vencimiento | No se usa | Responde PA8 leyendo 60 veces menos puntos | ~290 mil puntos para el torneo | Despreciable |
| Sin retención (alternativa descartada) | Igual | Igual | Crece sin límite con cada torneo | Creciente, y las consultas amplias leen más archivos |
| Retención 1d (alternativa descartada) | Igual | Se pierde el análisis del rival antes del siguiente partido | Mínimo | — |

## Implementación

- Retención: `crear_bases.sh` (`influxdb3 create database --retention-period 14d` / `none`).
- Downsampling: `downsampling.py` lee la ventana cerrada de cada partido, agrega con `date_bin(INTERVAL '1 minute', time)` y escribe en la base histórica. Es idempotente (mismos timestamps = sobrescritura).
- En producción: un trigger programado del Processing Engine de InfluxDB 3 ejecutaría lo mismo cada minuto sobre el minuto anterior. En el laboratorio se ejecuta a demanda para que sea reproducible.
- Verificación: la tabla de salida de `downsampling.py` muestra puntos crudos vs resumidos (reducción ~60x en las tablas de 1 Hz) y `a07_historico_1m.sql` responde la misma comparación que `c03` desde el histórico.
