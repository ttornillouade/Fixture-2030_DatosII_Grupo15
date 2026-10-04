-- titulo: Ventana reciente — últimos 2 minutos respecto de now()
-- patron: PA1 (estado en vivo)
-- opcional: si
-- interpretacion: Solo devuelve filas mientras corre scripts/simulador_vivo.py (o hubo escrituras en los últimos 2 min). Sin filas = la fuente no está enviando datos; la aplicación debe mostrar el último valor conocido con la marca "sin actualización desde ...".
SELECT time, partido_id, equipo_id, minuto, posesion_pct, pases_intentados, tiros, goles
FROM estadisticas_equipo
WHERE time >= now() - INTERVAL '2 minutes'
ORDER BY time DESC
LIMIT 10
