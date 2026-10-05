-- titulo: Ventana temporal — estadísticas de ambos equipos entre el minuto 60 y 65
-- patron: PA2 (ventana de un partido)
-- interpretacion: 1 punto por segundo y equipo (2 x 300 = 600 filas). Los contadores (pases, tiros) solo crecen; la posesión es el % acumulado del partido.
SELECT time, equipo_id, condicion, minuto, posesion_pct,
       pases_intentados, pases_completados, tiros, goles
FROM estadisticas_equipo
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{VENTANA_DESDE}}' AND time < '{{VENTANA_HASTA}}'
ORDER BY time, equipo_id
