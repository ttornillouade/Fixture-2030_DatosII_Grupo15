# Demostración controlada (RF13, RF16, RNF7)

Secuencia corta y reproducible. Todo con datos de laboratorio. Los comandos se ejecutan desde la raíz del
repositorio salvo que se indique otra carpeta.

## Preparación (antes de la defensa, ~10 minutos)

```bash
cd hito-10-api && bash scripts/levantar_todo.sh
```

```bash
cd hito-10-api && CACHE_COMENTARIOS_TTL_MS=1000 bash scripts/iniciar_api.sh
```

```bash
cd hito-13-monitoreo && bash scripts/iniciar_monitoreo.sh
```

```bash
cd hito-10-api && bash scripts/preparar_datos_demo.sh
```

1. Las seis bases con datos (Hitos 4-9) y el diagnóstico de conectividad.
2. La API con la caché del Hito 12 activa (en otra terminal; queda corriendo).
3. Prometheus, Grafana y exporters; al final imprime la tabla de targets (todos `up`).
4. Deja P128 en `PROGRAMADO` y la sesión `s-demo-001` (para repetir la demo).

Abrir antes, en pestañas: Grafana `http://localhost:3000/d/fixture2030` (últimos 15 min), Swagger
`http://localhost:8000/docs`, Prometheus `http://localhost:9090/alerts`, `defensa/presentacion.html`.

Para tener tráfico en los paneles durante la defensa (opcional, liviano: ~12 req/s):

```bash
cd hito-12-carga-optimizacion && .venv/bin/python scripts/ejecutar_carga.py --etiqueta demo --escenario config/escenario_demo.json
```

## Secuencia de la demo (bloque 4 del guion, ~4 minutos)

**Paso 1 — Salud y aislamiento** (`GET /salud/dependencias` en Swagger): las 6 bases `up`, con el tiempo de
ping de cada una. "Cada base se diagnostica por separado; esto mismo alimenta el panel de disponibilidad".

**Paso 2 — Lectura documental y de grafo**: `GET /equipos/E010` (MongoDB, ficha por `_id`) y
`GET /jugadores/E001-J09/partidos` (Neo4j, recorrido jugador → partidos → rival). "La segunda pregunta
son saltos entre nodos: por eso es un grafo".

**Paso 3 — Comentarios en vivo (Cassandra + Redis)**:
- `POST /partidos/P001/comentarios` con `{"usuarioId": "U000042", "texto": "Gol en la demo"}` → 201.
- `GET /partidos/P001/comentarios?bucket=<ventana actual>&limit=20` dos veces seguidas: la segunda sale de
  la caché (mostrar en Grafana el panel *Caché de comentarios: aciertos*). "El feed puede llegar con hasta
  1 s de atraso: es el trade-off que medimos en el Hito 12".

**Paso 4 — Entidad compleja con reglas (IRIS)**:
- `PATCH /partidos/P128/estado` `{"estado": "FINALIZADO"}` → **409** (no se puede saltear `EN_JUEGO`).
- `PATCH /partidos/P128/estado` `{"estado": "EN_JUEGO"}` → 200, y `GET /partidos/P128/detalle`.
- "Acá necesitamos consistencia fuerte: el estado del partido no puede ser eventual".

**Paso 5 — Falla controlada en vivo (opcional, 1-2 minutos)**:

```bash
docker stop fixture2030-cassandra
```

En Grafana: *Bases según la API* → Cassandra CAÍDA en ≤15 s, sonda TCP en rojo, aparecen 503 en
*Respuestas no exitosas*; MongoDB y Redis siguen con 2xx. En Prometheus → Alerts: `BaseNoDisponible`
pasa a *firing* a los 30 s.

```bash
docker start fixture2030-cassandra
```

Cassandra tarda ~30-60 s en volver a estar sana; la API se recupera sola (vuelve a abrir la sesión del
driver), sin reiniciarla.

## Plan B (si algo falla durante la defensa, RNF7)

| Si falla... | Alternativa preparada |
|---|---|
| Docker o una base no arranca | Mostrar la evidencia guardada: `evidencia/prometheus_targets.json`, `evidencia/prueba_de_falla_*/` (gráfico, capturas de Grafana, eventos) |
| La API no levanta | Respuestas guardadas por la colección Bruno del Hito 10 (`hito-10-api/docs/evidencia/`) y salidas del Hito 11 |
| Grafana no carga | Capturas en `evidencia/dashboards/` y el gráfico `prueba_de_falla.png` (generado desde Prometheus) |
| No hay red o proyector | `defensa/presentacion.html` funciona sin conexión (no carga nada externo) |
| Se acaba el tiempo | Saltear el paso 5: la prueba de falla ya está documentada con evidencia |

## Después de la demo

```bash
cd hito-10-api && bash scripts/preparar_datos_demo.sh
```

Vuelve P128 a `PROGRAMADO` y recrea la sesión de prueba, para poder repetir la demo.
