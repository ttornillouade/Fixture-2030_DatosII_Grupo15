# Pruebas y evidencia

## Método

| Paso | Script | Qué se mide / registra |
|---|---|---|
| Ambiente | `ambiente.sh` | fecha, SO, CPU, RAM, versión de Docker, recursos de la VM de Docker, versión de InfluxDB y digest de `influxdb:3-core` |
| Generación | `generacion_puntos.py` | puntos por tabla, tiempo y puntos/s (fuera del tiempo de carga) |
| Carga | `carga_lotes.py` | puntos aceptados/rechazados, segundos, puntos/s, latencia de lote p50/p95/máx, reintentos |
| Recursos | `docker stats`, `du -sh` | CPU/memoria del contenedor y disco usado |
| Validación | `validacion.py` | conteos, series, distribución y tipos vs manifiesto |
| Consultas | `consultar.py --repeticiones 5` | mediana, mínimo y máximo por consulta, medidos desde el cliente HTTP |

```bash
bash scripts/generar_evidencia.sh demo
bash scripts/prueba_rendimiento.sh lab 5000 4 5
```

Los tiempos de consulta incluyen red local y serialización JSON; no son tiempos internos del motor.
La primera ejecución de cada consulta puede ser más lenta (archivos aún no cacheados): por eso se repite 5 veces y se informa la mediana.

## Resultados

Fuente: `docs/evidencia/rendimiento_hito8_20261004_205417.txt`, `docs/evidencia/carga_20261004_205601.json`
y `docs/evidencia/tiempos_consultas_20261004_205417.json`.

| Dato | Valor |
|---|---|
| Fecha de ejecución | 2026-10-04 20:54 (-03) / 2026-10-04T23:54:17Z |
| Equipo (CPU / RAM / SO) | Apple M5 (10 núcleos) / 16 GB / macOS (Darwin 25.5.0 arm64) |
| Recursos asignados a Docker | Docker 29.5.3, VM con 10 CPUs y 7,75 GiB |
| Versión de InfluxDB observada (`influxdb3 --version`) | InfluxDB 3 Core 3.12.0 (imagen `influxdb:3-core`) |
| Perfil y puntos cargados | `lab`: 12 partidos, 1.999.014 puntos (290 tardíos) |
| Lote / hilos | 5.000 / 4 |
| Tiempo de carga y puntos/s | 101,8 s — 19.645 puntos/s |
| Latencia de lote p50 / p95 | 998,4 ms / 1.025,5 ms (máx. 1.138,2 ms) |
| Líneas rechazadas / lotes fallidos | 0 / 0 (405 lotes OK, 0 reintentos) |
| Validación | OK |
| Consulta más lenta (mediana) | `c05_comparacion_sedes.sql` — 44,3 ms (5 ejecuciones) |
| Disco usado por `~/docker/data/influxdb` | 163 MB (memoria del contenedor: 424,8 MiB) |

`c06_ventana_reciente.sql` y `a07_historico_1m.sql` devuelven 0 filas en esta corrida, como
se espera: la primera solo tiene datos mientras corre `simulador_vivo.py` y la segunda requiere
`downsampling.py`, que esta prueba no ejecuta. Ambas devuelven filas en la evidencia funcional
(`evidencia_hito8_20261004_205024.txt`).

### Proyección a 10M+ (no medida)

```text
tiempo estimado de carga del torneo = 17.304.177 puntos / (puntos/s medidos con el perfil lab)
                                    = 17.304.177 / 19.645 ≈ 881 s ≈ 14,7 minutos
```

Es una extrapolación lineal: supone el mismo equipo, el mismo lote y los mismos hilos, y que el
rendimiento no cae al crecer el volumen.

Si el equipo lo permite, ejecutar `prueba_rendimiento.sh torneo` y reemplazar la proyección por la medición.

## Verificación funcional previa (sin InfluxDB real)

Durante el desarrollo, los scripts de Python se probaron de punta a punta contra un servidor
HTTP simulado que reproduce `write_lp` (tipos, rechazo parcial, sobrescritura por serie +
timestamp) y `query_sql` (subconjunto de SQL). Con el perfil demo (329.908 puntos):
generación OK, carga sin rechazos, validación OK, downsampling con reducción 60x, rechazo
de 3 de 5 líneas en `--demo-errores`, reintentos ante servidor caído y aborto ante token
inválido. **Esa prueba no reemplaza la evidencia sobre InfluxDB real**: las funciones propias
de InfluxDB (`date_bin_gapfill`, `locf`, `last_cache`, retención) se verifican al ejecutar
`generar_evidencia.sh` con el contenedor.

## Limitaciones

- Calendario comprimido (4 partidos cada 3 h) para que todo el volumen quede dentro de la retención del vivo.
- Datos sintéticos: la distribución de eventos es plausible, no real.
- Un solo nodo y cliente en la misma máquina: compiten por CPU, lo que subestima el throughput de un servidor dedicado.
