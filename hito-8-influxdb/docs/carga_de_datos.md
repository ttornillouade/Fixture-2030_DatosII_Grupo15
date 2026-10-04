# Carga de datos

Generación, carga y validación son **tres scripts separados** (RF7, RNF9):

```text
generacion_puntos.py  ->  data/generated/<corrida>/*.lp.gz + manifest.json
carga_lotes.py        ->  POST /api/v3/write_lp?db=fixture2030_vivo&precision=millisecond
validacion.py         ->  consultas de control vs manifest.json
```

## Origen y generación

- Simulación determinística por partido (`random.Random("<semilla>-<partido>")`): misma semilla = mismos valores, aunque se generen en paralelo.
- Calendario de 104 partidos: 72 de grupos (12 grupos de 4) + 32 de eliminación; 3 partidos inaugurales en Uruguay, Argentina y Paraguay y el resto en España, Portugal y Marruecos.
- Los contadores de `estadisticas_equipo` se derivan de los mismos eventos generados, lo que permite validar la coherencia entre tablas.
- 2 % de los eventos se separan en `tardios.lp.gz` y se cargan al final para simular datos tardíos.
- El manifiesto guarda semilla, precisión, calendario, ventanas de cada partido, conteos esperados por tabla y partido, series esperadas y tipos.

## Volumen

| Perfil | Partidos | Puntos | Uso |
|---|---|---|---|
| demo | 2 | ~330 mil | evidencia funcional rápida |
| lab | 12 | ~2 M | medición en notebook (RF13) |
| torneo | 104 | 17,3 M | objetivo 10M+; generación medida, carga según hardware |

## Timestamps

- Epoch en **milisegundos**, `precision=millisecond` en cada request.
- Jitter de 0–250 ms en mediciones de 1 Hz (latencia del proveedor) y de 0–999 ms en eventos.
- Unicidad: si dos eventos de la misma serie caen en el mismo ms, el generador corre el segundo 1 ms (si no, InfluxDB sobrescribiría el primero).
- Por defecto el calendario se ancla a las últimas horas (dentro de la retención de 14 días). Con `--inicio 2030-06-13T16:00:00Z` se usa una fecha fija.

## Lotes y concurrencia

| Parámetro | Valor por defecto | Motivo |
|---|---|---|
| Tamaño de lote | 5.000 líneas (≤ 8 MB) | ~0,75 MB por request: amortiza el overhead HTTP sin requests gigantes |
| Hilos | 4 | el servidor confirma cada escritura al persistir el WAL (por defecto cada 1 s); varias requests en paralelo aprovechan esa espera |
| Cola | 2 x hilos lotes en vuelo | memoria constante aunque se carguen 17 M puntos |
| Orden | cada partido en orden temporal; partidos intercalados | simula la llegada real (varias fuentes en paralelo) |

`prueba_rendimiento.sh` permite medir otras combinaciones (`BARRIDO="1000x1 5000x4 10000x8"`).

## Manejo de errores

| Respuesta | Acción |
|---|---|
| 204 | lote aceptado |
| 400 con `partial write` | las líneas válidas quedan escritas; las inválidas se cuentan y se registran (no se reintenta: el dato es inválido) |
| 401 / 403 | se aborta la carga (token inválido) |
| 408, 429, 5xx, error de red, timeout | reintento con backoff exponencial (0,5 s, 1 s, 2 s... máx. 15 s) + jitter, hasta 5 veces |
| reintentos agotados | lote descartado y contado en `lotes_fallidos`; el script termina con código 1 |

Las escrituras son **idempotentes**: recargar el mismo archivo sobrescribe los mismos puntos (misma serie y timestamp). Por eso un reintento después de un timeout no duplica datos.

## Validación

`validacion.py` verifica, con consultas acotadas por partido:

1. puntos por tabla y partido = manifiesto (incluye los tardíos);
2. series por tabla y partido = manifiesto;
3. 60 puntos por equipo y minuto de juego y 0 puntos en el entretiempo;
4. `max(pases_intentados)` = cantidad de eventos `pase` = valor del manifiesto;
5. tipos de cada columna en `information_schema.columns`.

## Métricas que se registran

`docs/evidencia/carga_<fecha>.json`: puntos enviados/aceptados/rechazados, lotes, reintentos, segundos, puntos/s, latencia de lote p50/p95/máx, versión de Python y SO del cliente.
