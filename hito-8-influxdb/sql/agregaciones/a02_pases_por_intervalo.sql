-- titulo: Pases por intervalo de 5 min a partir de un contador acumulado (max + diferencia)
-- patron: PA3
-- interpretacion: pases_intentados es acumulado: el max de cada bloque es el total hasta ese momento y la diferencia con el bloque anterior es la cantidad de pases EN el bloque. Sumar el contador daría un número sin sentido.
SELECT time, equipo_id, pases_acumulados,
       pases_acumulados - coalesce(lag(pases_acumulados) OVER (PARTITION BY equipo_id ORDER BY time), 0)
         AS pases_en_intervalo
FROM (
  SELECT date_bin(INTERVAL '5 minutes', time) AS time,
         equipo_id,
         max(pases_intentados) AS pases_acumulados
  FROM estadisticas_equipo
  WHERE partido_id = '{{PARTIDO}}'
    AND time >= '{{JUEGO_DESDE}}' AND time < '{{JUEGO_HASTA}}'
  GROUP BY 1, equipo_id
) AS bloques
ORDER BY time, equipo_id
