# Checklist de requisitos — Hito 8

| ID | Requisito | Dónde se cumple |
|---|---|---|
| RF1 | Docker Compose + verificación con herramientas del contenedor | `docker-compose.yml`, `scripts/inicializacion.sh` (`influxdb3 --version`, `show databases`) |
| RF2 | Patrones de acceso antes del modelo | `docs/patrones_de_acceso.md` |
| RF3 | Modelo de observaciones temporales | `docs/modelo_multidimensional.md`, `scripts/generacion_puntos.py` |
| RF4 | Dimensiones partido / equipo / sede / jugador / plataforma | tags; consultas c01–c05 |
| RF5 | ≥ 3 medidas de distinta naturaleza | gauge, contador acumulado, evento, delta, percentil, booleano |
| RF6 | Precisión temporal | milisegundos: `PRECISION_LP`, manifiesto, `precision=millisecond` |
| RF7 | Carga reproducible separando generación, carga y validación | `generacion_puntos.py`, `carga_lotes.py`, `validacion.py` |
| RF8 | Ventana, comparación de dimensiones, agregados | `sql/consultas/`, `consultas_temporales.sh` |
| RF9 | Agregación justificada | `sql/agregaciones/`, `docs/consultas_y_agregaciones.md` |
| RF10 | Retención / granularidad / resumen | `crear_bases.sh`, `downsampling.py`, `docs/retencion_y_granularidad.md` |
| RF11 | Cardinalidad y tags vs fields | `docs/cardinalidad_y_escalabilidad.md`, `validacion.py` (V2) |
| RF12 | Estrategia para 10M+ | `carga_lotes.py`, `docs/carga_de_datos.md`, perfil `torneo` (17,3 M) |
| RF13 | Medición de carga y consulta | `prueba_rendimiento.sh`, `docs/pruebas_y_evidencia.md` |
| RF14 | Evidencia verificable | `generar_evidencia.sh`, `docs/evidencia/` |
| RNF1 | `influxdb:3-core` (el tag `influxdb:latest` de Docker Hub apunta a InfluxDB 2.x; ver comentario en el compose) | `docker-compose.yml` |
| RNF2 | `~/docker/data/influxdb` | `docker-compose.yml` |
| RNF3 | Reproducible siguiendo el README | `README.md` pasos 1–13 |
| RNF4 | Diseño dirigido por consultas | tabla patrón → tabla/tag/consulta en `patrones_de_acceso.md` |
| RNF5 | Cardinalidad estimada y medida | `cardinalidad_y_escalabilidad.md`, `validacion.py` |
| RNF6 | Tipos y precisión declarados | `modelo_multidimensional.md`, `validacion.py` (V5) |
| RNF7 | Sin secretos | `.gitignore`, `seguridad_local.md`, `enmascarar` |
| RNF8 | Consultas acotadas y rendimiento con método | todas las consultas con rango; `pruebas_y_evidencia.md` |
| RNF9 | Scripts separados por responsabilidad | `scripts/` |
| RNF10 | Evidencia con fecha, versión, recursos y volumen | `ambiente.sh`, `carga_*.json`, `rendimiento_hito8_*.txt` |
| RNF11 | Repositorio GitHub con historial | completar el enlace al inicio de `README.md` |

## Pendiente del equipo antes de entregar

- [x] Ejecutar `generar_evidencia.sh demo` y `prueba_rendimiento.sh lab` con el contenedor real.
- [x] Completar la tabla de resultados de `pruebas_y_evidencia.md` con esos archivos.
- [x] Agregar el enlace del repositorio al inicio de `README.md` y subir con commits incrementales.
