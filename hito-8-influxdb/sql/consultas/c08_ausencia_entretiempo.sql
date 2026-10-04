-- titulo: Ausencia de puntos — entretiempo con date_bin_gapfill
-- patron: PA2 / respuesta ante ausencia de puntos
-- interpretacion: Los minutos del entretiempo aparecen con muestras = NULL (no hubo puntos) y la posesión se rellena con el último valor conocido (locf). Así se distingue "sin dato" de "valor 0".
SELECT date_bin_gapfill(INTERVAL '1 minute', time) AS time,
       equipo_id,
       count(*)                AS muestras,
       locf(avg(posesion_pct)) AS posesion_pct_locf
FROM estadisticas_equipo
WHERE partido_id = '{{PARTIDO}}'
  AND equipo_id = '{{EQUIPO_LOCAL}}'
  AND time >= '{{HT_DESDE}}' AND time < '{{HT_HASTA}}'
GROUP BY 1, equipo_id
ORDER BY 1
