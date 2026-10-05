-- titulo: Eventos por tipo y equipo (eventos -> count / sum)
-- patron: PA5
-- interpretacion: Cada fila de eventos_partido es una ocurrencia: la agregación correcta es COUNT (o SUM(valor)). efectividad = exitosos / total, solo donde tiene sentido (pase completado, tiro al arco).
SELECT equipo_id, tipo_evento,
       count(*)                                                     AS cantidad,
       sum(valor)                                                   AS suma_valor,
       sum(CASE WHEN exitoso THEN 1 ELSE 0 END)                     AS exitosos,
       CASE WHEN tipo_evento IN ('pase', 'tiro')
            THEN round(100.0 * sum(CASE WHEN exitoso THEN 1 ELSE 0 END) / count(*), 1)
       END                                                          AS efectividad_pct,
       round(sum(xg), 2)                                            AS xg_total
FROM eventos_partido
WHERE partido_id = '{{PARTIDO}}'
  AND time >= '{{PARTIDO_DESDE}}' AND time < '{{PARTIDO_HASTA}}'
GROUP BY equipo_id, tipo_evento
ORDER BY equipo_id, cantidad DESC
