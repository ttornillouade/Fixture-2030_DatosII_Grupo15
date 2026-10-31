# Evidencia — Hito 11

Salidas de los scripts, tal como se generan: ya están redactadas. Las variables secretas aparecen
como `definida (oculta)`, las URIs con usuario como `//***@`, y las rutas personales como `~`. Al
final, `evaluar_conectividad.sh` verifica que ningún valor secreto del `.env` aparezca en esta carpeta.
No hay capturas de pantalla: toda la evidencia es texto.

| Archivo | Generado por | Contenido |
|---|---|---|
| `resultados_tcp.txt` | `evaluar_conectividad.sh` | Configuración, resolución y TCP de cada destino, y los contrastes de la tabla 5.3 |
| `resultados_clientes.txt` | `evaluar_conectividad.sh` | Protocolo, identidad, contexto y lectura de cada producto, y sus contrastes |
| `resultados_api.txt` | `evaluar_conectividad.sh` | Rutas del Hito 10 con status, duración, `requestId` y línea de log |
| `resultados.jsonl` | `evaluar_conectividad.sh` | Lo mismo, una prueba por línea (fecha, producto, capa, tipo, resultado, ms, detalle) |
| `matriz.md` | `evaluar_conectividad.sh` | Estado por producto, con fecha, commit y modo |
| `falla_<accion>_<producto>.txt` | `prueba_falla.sh` | Condición inicial, cambio, respuesta, log, recuperación y datos conservados |

Cada archivo empieza con la fecha, el commit (con la marca "cambios sin commit" si corresponde), el
entorno (notebook, Python, Docker) y el origen de las pruebas (RNF18). `api.log`, la salida cruda de
la API, no se versiona.
