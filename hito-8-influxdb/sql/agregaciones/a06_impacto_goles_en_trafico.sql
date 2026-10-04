-- titulo: Impacto de los goles en el tráfico (eventos + actividad por minuto)
-- patron: PA6 + PA5 — interpretación en el contexto del partido
-- interpretacion: Cruza dos tablas en el mismo bin de 1 minuto. En los minutos con gol las solicitudes por segundo suben respecto del promedio del partido: la plataforma debe dimensionarse para esos picos, no para el promedio.
SELECT t.time,
       t.solicitudes_por_seg,
       coalesce(g.goles, 0) AS goles_en_el_minuto
FROM (
  SELECT date_bin(INTERVAL '1 minute', time) AS time,
         round(sum(solicitudes) / 60.0, 0) AS solicitudes_por_seg
  FROM actividad_usuarios
  WHERE partido_id = '{{PARTIDO}}'
    AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
  GROUP BY 1
) AS t
LEFT JOIN (
  SELECT date_bin(INTERVAL '1 minute', time) AS time, count(*) AS goles
  FROM eventos_partido
  WHERE partido_id = '{{PARTIDO}}' AND tipo_evento = 'gol'
    AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
  GROUP BY 1
) AS g ON t.time = g.time
ORDER BY t.solicitudes_por_seg DESC
LIMIT 10
