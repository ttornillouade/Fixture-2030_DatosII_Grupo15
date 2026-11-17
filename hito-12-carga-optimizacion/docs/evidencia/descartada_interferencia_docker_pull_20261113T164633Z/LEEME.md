# Corrida descartada (no forma parte de la comparación)

Primera ejecución de `linea_base_r1`. Durante el segundo ~50 del sostenimiento Cassandra dejó de responder
~5,8 s: 45 respuestas `504 DEPENDENCY_TIMEOUT`, 20 timeouts del cliente y corte automático por la regla de
interrupción segura (>20 % de error en las últimas 100 requests de un proceso del generador).

Causa identificada: en ese mismo momento se estaban descargando 5 imágenes de Docker para el Hito 13
(`docker pull` dentro de la misma VM de Docker Desktop). El log de GC de Cassandra no muestra pausas
largas en esa ventana (pausas jóvenes de 5-13 ms), y Cassandra registró `MUTATION_REQ messages were
dropped ... Mean internal dropped latency: 2464 ms`, compatible con falta de CPU/E/S en la VM.

Se conserva porque es evidencia real útil:
- la validación de integridad encontró **10 comentarios escritos en Cassandra cuyo POST el cliente dio
  por fallido** (timeout del cliente o 504 de la API después de que el batch ya se había aplicado):
  `sobrantes_vs_201 = 10`. Un código HTTP de error no garantiza que el dato no se haya escrito
  (ver docs/integridad_y_limitaciones.md);
- además, la medición de CPU de la API salía en 0 % por un error del script (se corrigió antes de repetir).

La línea base se volvió a ejecutar completa, sin otras tareas en paralelo.
