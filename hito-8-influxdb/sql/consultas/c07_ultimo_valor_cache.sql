-- titulo: Último valor por equipo desde la Last Value Cache
-- patron: PA1 (estado en vivo)
-- opcional: si
-- interpretacion: Requiere scripts/caches_ultimo_valor.sh. La LVC mantiene en memoria el último punto de cada combinación (partido_id, equipo_id) y responde sin leer Parquet.
SELECT *
FROM last_cache('estadisticas_equipo', 'ultimo_estado_equipo')
ORDER BY partido_id, equipo_id
