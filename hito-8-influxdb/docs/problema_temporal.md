# Problema temporal

## Qué se registra

Durante cada partido del Mundial 2030 llegan observaciones que cambian de forma continua.
El módulo trabaja con cuatro fenómenos de naturaleza distinta:

| Fenómeno | Fuente | Frecuencia | Naturaleza de las medidas |
|---|---|---|---|
| Estadísticas del equipo | proveedor de datos del partido | 1 punto/s por equipo | contadores acumulados (pases, tiros, goles) y un porcentaje acumulado (posesión) |
| Rendimiento físico del jugador | sistema de tracking (agregado a 1 Hz) | 1 punto/s por jugador en cancha | gauge (velocidad) y contadores acumulados (distancia, sprints) |
| Eventos del partido | proveedor / operador de datos | irregular (~1.350 por partido) | ocurrencias discretas (pase, tiro, gol, falta, ...) |
| Actividad de la plataforma | backend de la aplicación (sesiones del Hito 7) | 1 punto/s por plataforma | gauge (usuarios activos), deltas (solicitudes, errores) y un percentil ya calculado (latencia p95) |

## Volumen esperado

Por partido (90 min + adiciones, entretiempo de 15 min, actividad desde 15 min antes hasta 15 min después):

| Tabla | Cálculo | Puntos/partido |
|---|---|---|
| estadisticas_equipo | 2 equipos x ~5.700 s de juego | ~11.500 |
| rendimiento_jugador | 22 jugadores x ~5.700 s | ~127.000 |
| eventos_partido | ~1.350 eventos | ~1.350 |
| actividad_usuarios | 3 plataformas x ~8.400 s | ~25.400 |
| **Total** | | **~166.000** |

104 partidos ≈ **17,3 M puntos** (cantidad medida por el generador con el perfil `torneo`),
por encima del objetivo de 10 M.

## Decisiones que se toman en tiempo real

- Mostrar el estado actual del partido (posesión, tiros, goles) en la app y en pantallas: lectura del último valor con latencia de segundos.
- Avisar al cuerpo técnico de la carga física de un jugador (velocidad media, distancia y sprints de los últimos minutos).
- Operación de la plataforma: detectar picos de tráfico (por ejemplo después de un gol) y degradación de latencia o errores por plataforma.
- Detectar que una fuente dejó de enviar datos (ausencia de puntos) y distinguirlo de un valor real 0.

Después del partido y durante el torneo, las mismas series se usan para análisis histórico,
con una granularidad menor (1 minuto).
