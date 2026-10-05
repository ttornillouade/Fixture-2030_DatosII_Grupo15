-- titulo: Top 10 jugadores por distancia recorrida en el partido
-- patron: PA4
-- interpretacion: distancia_m es acumulada por jugador: max = distancia total. velocidad es una muestra instantánea: avg = ritmo medio, max = pico. Los suplentes muestran menos distancia porque tienen menos minutos (menos puntos).
SELECT jugador_id, equipo_id,
       round(max(distancia_m) / 1000, 2)  AS distancia_km,
       round(avg(velocidad_kmh), 2)       AS velocidad_avg_kmh,
       round(max(velocidad_kmh), 2)       AS velocidad_max_kmh,
       max(sprints)                       AS sprints,
       round(count(*) / 60.0, 1)          AS minutos_con_datos
FROM rendimiento_jugador
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
GROUP BY jugador_id, equipo_id
ORDER BY distancia_km DESC
LIMIT 10
