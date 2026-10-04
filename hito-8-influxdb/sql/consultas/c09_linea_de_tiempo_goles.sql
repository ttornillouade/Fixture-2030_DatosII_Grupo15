-- titulo: Línea de tiempo de tiros y goles del partido
-- patron: PA5 (eventos del partido)
-- interpretacion: Los eventos tienen timestamp irregular (ms). jugador_id es un field (no tag): se devuelve como dato sin multiplicar series.
SELECT time, minuto, equipo_id, tipo_evento, jugador_id, exitoso AS al_arco, round(xg, 3) AS xg
FROM eventos_partido
WHERE partido_id = '{{PARTIDO}}'
  AND tipo_evento IN ('tiro', 'gol')
  AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
ORDER BY time
