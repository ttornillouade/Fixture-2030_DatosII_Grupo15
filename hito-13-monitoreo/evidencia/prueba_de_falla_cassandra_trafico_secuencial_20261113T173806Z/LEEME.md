# Primera prueba de falla (tráfico secuencial) — se conserva, pero no es la evidencia principal

El cliente de prueba de esta corrida usaba **un solo hilo** para las tres bases. Cuando las requests a Cassandra
tardaban (hasta 10 s, ver `series.csv`), el hilo quedaba esperando y dejaba de enviar requests a MongoDB y Redis:
en el gráfico, el tráfico de esas bases cae a cero durante la caída. **Es un artefacto del cliente**, no de la API:
en el log de la API, las requests de MongoDB y Redis de ese período respondieron en ~9 ms.

Se corrigió el script (un hilo por base) y se repitió: ver `prueba_de_falla_cassandra_20261113T174247Z` (antes del
corte rápido) y la corrida posterior (con el corte rápido). Lo que sí vale de esta corrida: las alertas
`BaseNoDisponible` y `SondaTCPFallando` se dispararon, y `/salud/dependencias` tardó 10,05 s durante la caída.
