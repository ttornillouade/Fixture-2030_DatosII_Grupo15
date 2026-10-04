-- titulo: Posesión por bloques de 15 minutos (gauge -> avg y último valor)
-- patron: PA3 / PA8
-- interpretacion: posesion_pct es un porcentaje acumulado: el valor al final del bloque (last_value) es la posesión del partido hasta ese momento; el promedio describe el bloque. Sumarla no tiene significado.
SELECT date_bin(INTERVAL '15 minutes', time) AS time,
       equipo_id,
       round(avg(posesion_pct), 2)                      AS posesion_avg,
       round(last_value(posesion_pct ORDER BY time), 2) AS posesion_al_cierre,
       count(*)                                         AS muestras
FROM estadisticas_equipo
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
GROUP BY 1, equipo_id
ORDER BY 1, equipo_id
