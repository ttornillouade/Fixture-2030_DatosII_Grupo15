# Patrones de acceso — Hito 7

El diseño parte de operaciones concretas y no de una lista arbitraria de estructuras Redis.

| Patrón | Quién lo usa | Entrada | Respuesta | Frecuencia | Estructura |
|---|---|---|---|---|---|
| P1 Crear sesión | autenticación | session_id + user_id | sesión válida | media/alta | Hash + TTL |
| P2 Validar sesión | navegación autenticada | session_id | atributos de sesión o ausencia | muy alta | Hash |
| P3 Renovar sesión | actividad del usuario | session_id | TTL renovado | alta | MULTI/EXEC |
| P4 Cerrar sesión | logout/revocación | session_id | clave eliminada | media | DEL |
| P5 Leer equipo frecuente | navegación | equipo_id | ficha resumida | muy alta | Hash de caché |
| P6 Cache miss | aplicación | equipo_id | lectura de fuente de verdad + reconstrucción | media/baja | cache-aside |
| P7 Invalidar caché | escritura de negocio | equipo_id | copia obsoleta eliminada | baja | DEL |
| P8 Ranking temporal | navegación concurrente | partido_id | ranking de partidos consultados | alta | Sorted Set |
| P9 Inspección | operación | prefijo | claves acotadas | baja | SCAN |

## Decisión transversal

Los datos de sesión y caché son temporales. Redis no se convierte en fuente de verdad de Equipos ni Partidos.

- `Equipo`: fuente de verdad documental del Hito 4.
- `Partido`: identidad compartida con el Hito 5.
- Redis: estado transitorio, copia rápida y estructuras temporales.
