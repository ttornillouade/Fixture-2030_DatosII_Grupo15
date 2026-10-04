-- titulo: Comparación entre partidos — pico de audiencia simultánea por país sede y fase
-- patron: PA7 (comparar audiencia entre sedes)
-- interpretacion: Primero se suman las plataformas en el mismo segundo (sumar gauges de series distintas en un mismo instante es válido); después se toma el máximo por partido. Sumar usuarios a lo largo del tiempo sería un error semántico.
SELECT pais_sede, fase, partido_id,
       max(usuarios_total) AS pico_usuarios_simultaneos,
       round(avg(usuarios_total), 0) AS promedio_usuarios
FROM (
  SELECT date_bin(INTERVAL '1 second', time) AS segundo,
         pais_sede, fase, partido_id,
         sum(usuarios_activos) AS usuarios_total
  FROM actividad_usuarios
  WHERE time >= '{{TORNEO_DESDE}}' AND time < '{{TORNEO_HASTA}}'
  GROUP BY 1, pais_sede, fase, partido_id
) AS por_segundo
GROUP BY pais_sede, fase, partido_id
ORDER BY pico_usuarios_simultaneos DESC
