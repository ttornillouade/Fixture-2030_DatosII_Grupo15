-- titulo: Comparación de dimensiones — local vs visitante cada 5 minutos
-- patron: PA3 (comparar equipos dentro del partido)
-- interpretacion: Para cada bloque de 5 min se toma el último valor acumulado (max) de pases y tiros y el promedio de la posesión acumulada. Los bloques del entretiempo no aparecen porque no hay puntos.
SELECT date_bin(INTERVAL '5 minutes', time) AS time,
       equipo_id,
       condicion,
       round(avg(posesion_pct), 1) AS posesion_pct_avg,
       max(pases_intentados)       AS pases_intentados,
       max(pases_completados)      AS pases_completados,
       max(tiros)                  AS tiros,
       max(goles)                  AS goles
FROM estadisticas_equipo
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
GROUP BY 1, equipo_id, condicion
ORDER BY 1, condicion
