-- titulo: Filtro por dimensión — rendimiento físico de un jugador cada 30 s
-- patron: PA4 (rendimiento de un jugador)
-- interpretacion: Filtra por tres tags (partido, equipo, jugador) y una ventana de 5 min. velocidad = gauge (avg/max); distancia = contador acumulado (max = valor al final del intervalo).
SELECT date_bin(INTERVAL '30 seconds', time) AS time,
       jugador_id,
       round(avg(velocidad_kmh), 2) AS velocidad_avg_kmh,
       round(max(velocidad_kmh), 2) AS velocidad_max_kmh,
       round(max(distancia_m), 1)   AS distancia_acum_m,
       max(sprints)                 AS sprints_acum,
       count(*)                     AS muestras
FROM rendimiento_jugador
WHERE partido_id = '{{PARTIDO}}'
  AND equipo_id = '{{EQUIPO_LOCAL}}'
  AND jugador_id = '{{JUGADOR}}'
  AND time >= '{{VENTANA_DESDE}}' AND time < '{{VENTANA_HASTA}}'
GROUP BY 1, jugador_id
ORDER BY 1
