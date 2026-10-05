-- titulo: Actividad de la plataforma cada 10 min (gauge vs delta vs percentil)
-- patron: PA6
-- interpretacion: solicitudes/errores son deltas -> SUM; usuarios_activos es gauge -> AVG y MAX; latencia_p95 es un percentil ya calculado -> MAX (promediar percentiles no da el percentil del conjunto).
SELECT date_bin(INTERVAL '10 minutes', time) AS time,
       plataforma,
       round(avg(usuarios_activos), 0)          AS usuarios_avg,
       max(usuarios_activos)                    AS usuarios_max,
       sum(solicitudes)                         AS solicitudes,
       sum(errores)                             AS errores,
       round(max(latencia_p95_ms), 1)           AS latencia_p95_max_ms
FROM actividad_usuarios
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{PARTIDO_DESDE}}' AND time < '{{PARTIDO_HASTA}}'
GROUP BY 1, plataforma
ORDER BY 1, plataforma
