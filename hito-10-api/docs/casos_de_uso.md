# Casos de uso

Cada caso de uso lo atiende **una sola base**: la que mejor modela ese dato.

| # | Caso de uso | Consumidor | Entrada | Fuente | Respuesta | Si no existe | Si la base cae | Tipo | Éxito |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Ver la ficha de un equipo | App pública | `codigo` (E010) | MongoDB `equipos` | Código, nombre, país, confederación, grupo | 404 `TEAM_NOT_FOUND` | 503 | Lectura | 200 con la ficha |
| 2 | Ver el plantel de un equipo por posición | App pública | `equipoCodigo`, `posicion`, `limit`, `cursor` | MongoDB `jugadores` | Página por dorsal | 200 con página vacía | 503 | Lectura | 200 con la página y `nextCursor` |
| 3 | Ver el estado de un partido | Mesa de control | `codigo` (P001) | MongoDB `partidos` | Estado, fecha, sede, equipos, cantidad de eventos | 404 `MATCH_NOT_FOUND` | 503 | Lectura | 200 con el detalle |
| 4 | Iniciar o finalizar un partido | Mesa de control | `codigo`, `estado` | MongoDB `partidos` | Detalle con el estado nuevo | 404 | 503 | Actualización | 200; transición ilegal → 409 |
| 5 | Ver la evolución de un partido | Pantalla de estadísticas | `codigo`, `desde`, `hasta`, `agregacion` | MongoDB `estadisticas` (time series) | Puntos por equipo, crudos o por minuto | 200 con lista vacía | 503 | Lectura | 200 con los puntos |
| 6 | Ver la trayectoria de un jugador | App pública | `codigo` de jugador (E001-J09) | Neo4j (recorrido) | Partidos jugados, fase, titular y rival | 404 `PLAYER_NOT_FOUND` | 503 | Lectura | 200 con los partidos |
| 7 | Leer el feed de comentarios | App pública | `codigo`, `bucket` (5 min), `limit`, `cursor` | Cassandra | Comentarios más recientes primero | 200 con página vacía | 503 | Lectura | 200 con la página |
| 8 | Publicar un comentario | Usuario autenticado | `codigo`, `usuarioId`, `texto` | Cassandra (2 tablas) | Comentario con id y fecha | — | 503 | Creación | 201 |
| 9 | Validar una sesión | Backend | `sesionId` | Redis | Usuario, estado, segundos restantes | 404 `SESSION_EXPIRED_OR_NOT_FOUND` | 503 | Lectura | 200 |
| 10 | Cerrar una sesión | Backend | `sesionId` | Redis | — | 404 | 503 | Invalidación | 204 |
