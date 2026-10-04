-- titulo: Consulta sobre el histórico resumido (1 min) — misma pregunta, menos puntos
-- db: historico
-- patron: PA8 (análisis histórico)
-- opcional: si
-- interpretacion: Requiere scripts/downsampling.py. Se responde la comparación local/visitante cada 15 min leyendo ~1/60 de los puntos. Se pierde el detalle por segundo pero se conserva lo necesario para el análisis post-partido.
SELECT date_bin(INTERVAL '15 minutes', time) AS time,
       equipo_id,
       round(avg(posesion_pct_avg), 1) AS posesion_avg,
       max(pases_intentados)           AS pases_intentados,
       max(tiros)                      AS tiros,
       max(goles)                      AS goles,
       sum(muestras)                   AS puntos_crudos_representados
FROM estadisticas_equipo_1m
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
GROUP BY 1, equipo_id
ORDER BY 1, equipo_id
