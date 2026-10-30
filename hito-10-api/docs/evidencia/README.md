# Evidencia — Hito 10

`pruebas_<fecha>.txt` es la salida de `bash scripts/ejecutar_pruebas.sh` con las bases levantadas y la
API corriendo: conectividad de las 6 bases, verificación del contrato OpenAPI, colección Bruno completa,
contraste de cada endpoint con el cliente nativo de su base, dependencias caídas (Neo4j, Redis, IRIS e InfluxDB) y
latencia básica. Las contraseñas de Neo4j e IRIS y el token de InfluxDB se leen de `.env` y no se imprimen.
