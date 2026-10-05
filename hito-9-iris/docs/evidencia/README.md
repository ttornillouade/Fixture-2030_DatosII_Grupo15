# Evidencia — Hito 9

| Archivo | Lo genera | Contenido |
|---|---|---|
| `evidencia_hito9_<fecha>.txt` | `bash scripts/generar_evidencia.sh` | Ambiente y versión observada, arranque y compilación, bloque de comandos 5.3, demostración completa, consultas en el shell SQL y prueba de persistencia tras `docker compose down` + `up`. |

## Cómo leerla

| Sección | Qué demuestra |
|---|---|
| 0–1 | Fecha, sistema, imagen `latest-cd` con su digest, versión de IRIS, Durable %SYS en `~/docker/data/iris` y compilación sin errores (RF1, RNF1, RNF2). |
| 2 | Sesión de terminal con cada comando y su resultado (punto 5.3 de la consigna). |
| 3 | `do ##class(Fixture.Demo).Ejecutar()`: cada prueba indica `[esperado]` o `[INESPERADO]` y, si fue rechazada, el mensaje de IRIS. Al final, el total. |
| 4 | Consultas relacionales clásicas en el shell SQL de IRIS (RF8). |
| 5 | Mismos conteos y misma navegación antes y después de recrear el contenedor (RF1). |

La contraseña local nunca aparece en la salida: el script la reemplaza por `****OCULTO****` si la encuentra.

## Capturas

La evidencia es la salida de texto de la terminal de IRIS. Para una captura de pantalla,
abrir la terminal con `bash scripts/terminal.sh` y ejecutar `do ##class(Fixture.Demo).Ejecutar()`.
