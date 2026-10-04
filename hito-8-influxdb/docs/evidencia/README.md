# Evidencia — Hito 8

| Archivo | Lo genera | Contenido |
|---|---|---|
| `evidencia_hito8_<fecha>.txt` | `scripts/generar_evidencia.sh` | ambiente, disponibilidad, bases y retención, generación, carga, errores, validación, consultas, agregaciones, downsampling, ventana en vivo |
| `rendimiento_hito8_<fecha>.txt` | `scripts/prueba_rendimiento.sh` | ambiente, carga medida, recursos, validación y latencia de consultas |
| `carga_<fecha>.json` | `scripts/carga_lotes.py` | métricas de cada carga |
| `tiempos_consultas_<fecha>.json` | `scripts/consultar.py --guardar` | mediana/mín/máx por consulta |

Todos los tokens aparecen enmascarados (`apiv3_****OCULTO****`). Revisar antes de commitear.
