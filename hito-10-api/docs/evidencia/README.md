# Evidencia — Hito 10

`pruebas_<fecha>.txt` es la salida de `bash scripts/ejecutar_pruebas.sh` con las bases levantadas y la
API corriendo: conectividad de las 4 bases, verificación del contrato OpenAPI, colección Bruno completa,
contraste de cada endpoint con el cliente nativo de su base, dependencias caídas (Neo4j y Redis) y
latencia básica. La contraseña de Neo4j se lee de `.env` y no se imprime.
