# Casos de uso

Cada endpoint responde a un caso de uso del Fixture 2030 y lo atiende **una sola base**: la que
el TPO eligió para ese dato. No hay endpoints genéricos ni consultas enviadas por el cliente.

| # | Caso de uso | Consumidor | Entrada | Fuente | Respuesta | Si no existe | Si la base cae | Tipo | Éxito |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Ver la ficha de un equipo | App pública | `codigo` (E010) | MongoDB `equipos` | Código, nombre, país, confederación, grupo | 404 `TEAM_NOT_FOUND` | 503 | Lectura | 200 con la ficha |
| 2 | Ver el plantel de un equipo por posición | App pública | `equipoCodigo`, `posicion`, `limit`, `cursor` | MongoDB `jugadores` | Página de jugadores por dorsal | 200 con página vacía | 503 | Lectura | 200 con la página y `nextCursor` |
| 3 | Ver los hechos de un partido | App pública | `codigo` (P001) | Neo4j (Evento→Partido) | Eventos con tipo, minuto y jugador, por minuto | 404 `MATCH_NOT_FOUND`; un partido sin eventos da 200 con lista vacía | 503 | Lectura | 200 con los eventos |
| 4 | Leer el feed de comentarios de un partido | App pública | `codigo`, `bucket` (5 min), `limit`, `cursor` | Cassandra `comentarios_por_partido` | Comentarios más recientes primero | 200 con página vacía | 503 | Lectura | 200 con la página |
| 5 | Publicar un comentario | Usuario autenticado | `codigo`, `usuarioId`, `texto` | Cassandra (2 tablas) | Comentario creado con id y fecha | — | 503 | Creación | 201 con el comentario |
| 6 | Validar una sesión | Backend de la app | `sesionId` | Redis `fixture2030:session:*` | Usuario, estado, segundos restantes | 404 `SESSION_EXPIRED_OR_NOT_FOUND` | 503 | Lectura | 200 con la sesión |
| 7 | Iniciar y cerrar una sesión | Backend de la app | `usuarioId` / `sesionId` | Redis | Sesión creada (TTL 30 min) / 204 | DELETE: 404 | 503 | Creación / invalidación | 201 / 204 |
| 8 | Ver la evolución de un partido | Pantalla de estadísticas | `codigo`, `desde`, `hasta`, `agregacion` | InfluxDB `estadisticas_equipo` | Puntos por equipo (crudos o por minuto) | 200 con lista vacía (sin observaciones) | 503 | Lectura | 200 con los puntos |
| 9 | Ver el estado de un partido | Mesa de control | `codigo` | IRIS `Fixture.Partido` | Estado, sede, equipos, cantidad de eventos | 404 `MATCH_NOT_FOUND` | 503 | Lectura | 200 con el detalle |
| 10 | Iniciar o finalizar un partido | Mesa de control | `codigo`, `estado` | IRIS (`CambiarEstado`) | Detalle con el estado nuevo | 404 | 503 | Actualización | 200; transición ilegal → 409 |
