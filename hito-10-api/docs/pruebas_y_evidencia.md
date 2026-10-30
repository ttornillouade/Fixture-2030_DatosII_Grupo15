# Pruebas y evidencia

## Cómo se prueba

Con las bases levantadas y la API corriendo (`bash scripts/iniciar_api.sh`):

```bash
bash scripts/ejecutar_pruebas.sh
```

Guarda la salida en `docs/evidencia/pruebas_<fecha>.txt` y ejecuta:

1. **Conectividad** de las seis bases con su cliente nativo.
2. **Contrato:** `openapi/openapi.yaml` coincide con las rutas implementadas.
3. **Colección Bruno** (`bruno/`): 33 requests con tests de estado y de contenido.
4. **Contraste:** la respuesta de la API junto a la misma consulta hecha con el cliente nativo (RF17).
5. **Dependencias caídas:** se detienen Neo4j, Redis, IRIS e InfluxDB (sus datos persisten en disco) y se vuelven a levantar.
6. **Latencia básica.**

La colección también se abre en la app de Bruno (carpeta `bruno/`, entorno `local`).

## Cobertura (punto 5.12 de la consigna)

| Escenario | Dónde |
|---|---|
| Request válida por módulo | `01-mongodb-equipos` a `06-redis-sesiones` |
| Parámetro inválido (400) | `equipo-codigo-invalido`, `plantel-sin-equipo`, `codigo-invalido`, `estado-invalido`, `ventana-excedida`, `rango-invertido`, `jugador-codigo-invalido`, `sin-bucket`, `bucket-desalineado`, `crear-vacio` |
| Recurso inexistente (404) | `equipo-inexistente`, `02-iris-partidos/inexistente`, `jugador-inexistente` |
| Respuesta vacía válida (200) | `plantel-vacio`, `ventana-sin-puntos` |
| Sesión ausente o expirada (404) | `06-redis-sesiones/obtener-eliminada` |
| Conflicto (409) | `saltear-estado`, `iniciar-de-nuevo` |
| Escritura repetida | `crear-repetido` (otro `comentarioId`) e `iniciar-de-nuevo` (409, sin doble efecto) |
| Paginación y ventanas | `plantel` → `plantel-siguiente`, `pagina` → `siguiente-pagina`, `ventana-excedida` |
| Dependencia detenida (503) | Sección 5 de `ejecutar_pruebas.sh` |
| Documentación = respuesta real | Sección 2 (contrato) y los tests de Bruno |

Efectos de la colección: crea 2 comentarios, invalida la sesión `s-demo-001` y lleva P128 a
`FINALIZADO`. `scripts/preparar_datos_demo.sh` vuelve a crear la sesión y deja P128 en `PROGRAMADO`.

## Resultados (`docs/evidencia/pruebas_20261030_194256.txt`)

- Conectividad: las 6 bases OK; MongoDB con 64 equipos y 1.536 jugadores, InfluxDB con 45.600 puntos e IRIS
  con 128 partidos (127 del Hito 5 y P128 de prueba).
- Contrato: `openapi/openapi.yaml` coincide con el código.
- Bruno: 33/33 requests, 38/38 tests.
- Neo4j detenido: `GET /jugadores/E001-J09/partidos` responde 503 y `GET /partidos/P001/detalle` sigue en 200.
- Redis detenido: `GET /sesiones/s-demo-001` responde 503 y `GET /equipos/E011` sigue en 200.
- IRIS detenido: `GET /partidos/P001/detalle` responde 503 y `GET /equipos/E011` sigue en 200.
- InfluxDB detenido: `GET /partidos/P001/estadisticas` responde 503 y `GET /partidos/P001/detalle` sigue en 200.
- Al volver cada base, sus endpoints responden 200 sin reiniciar la API. Si una base no responde (en lugar
  de rechazar la conexión), el límite es `TIMEOUT_S` = 3 s.

## Rendimiento básico

- **Método:** 20 requests secuenciales por endpoint con `curl` (`time_total`); mediana, p95 y máximo.
- **Entorno:** API (uvicorn, 1 proceso) en la notebook y bases en Docker Desktop (Apple M5, 16 GB).
- **Volumen:** 64 equipos y 1.536 jugadores en MongoDB; 45.600 puntos en InfluxDB (4 partidos, 1 por segundo
  y equipo); 128 partidos y 508 eventos en IRIS; 127 partidos y 508 eventos en Neo4j; comentarios del Hito 6.
- **Resultado:** sección 6 de la evidencia (medianas de 3 a 15 ms; la agregación de una hora en InfluxDB y el
  recorrido del grafo son los más lentos).
- **Limitaciones:** sin concurrencia, sin red real, un nodo por base y datos en caché. Mide la sobrecarga de
  la API y los adaptadores, no la capacidad del sistema.

## Coherencia con el TPO

| Hito | Funcionalidad | Base | Endpoint |
|---|---|---|---|
| 4 | Equipos y jugadores | MongoDB | `/equipos/{codigo}`, `/jugadores` |
| 5 | Relaciones | Neo4j | `/jugadores/{codigo}/partidos` |
| 6 | Comentarios | Cassandra | `/partidos/{codigo}/comentarios` |
| 7 | Sesiones | Redis | `/sesiones/{id}` |
| 8 | Estadísticas temporales | InfluxDB | `/partidos/{codigo}/estadisticas` |
| 9 | Partido con estados | IRIS | `/partidos/{codigo}/detalle`, `/partidos/{codigo}/estado` |

Todos los módulos usan los mismos identificadores y fechas (los del Hito 5): `E001`, `E001-J09`,
`P001` y la fecha 2030-06-08 en MongoDB, Neo4j, Cassandra, InfluxDB e IRIS.
