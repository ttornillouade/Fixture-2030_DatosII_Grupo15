-- titulo: Comparación de fuentes — actividad por plataforma durante el partido
-- patron: PA6 (monitoreo operativo)
-- interpretacion: usuarios_activos es un gauge: se informa promedio y pico, nunca la suma en el tiempo. solicitudes y errores son deltas por segundo: se suman. La latencia p95 ya es un percentil: se toma el máximo.
SELECT plataforma,
       round(avg(usuarios_activos), 0)                              AS usuarios_avg,
       max(usuarios_activos)                                        AS usuarios_pico,
       sum(solicitudes)                                             AS solicitudes_total,
       sum(errores)                                                 AS errores_total,
       round(100.0 * sum(errores) / sum(solicitudes), 3)            AS tasa_error_pct,
       round(max(latencia_p95_ms), 1)                               AS latencia_p95_max_ms
FROM actividad_usuarios
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{PARTIDO_DESDE}}' AND time < '{{PARTIDO_HASTA}}'
GROUP BY plataforma
ORDER BY usuarios_pico DESC
