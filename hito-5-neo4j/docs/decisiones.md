# Decisiones de diseño — Hito 5

| Decisión | Alternativas consideradas | Elección | Justificación | Impacto |
|---|---|---|---|---|
| Alcance de `Jugador` | atributos propios + estadísticas / solo atributos propios | **Solo atributos propios** | Las métricas deportivas pertenecen a su módulo específico | Evita superposición entre tecnologías |
| `Grupo` | nodo / propiedad | **Propiedad de `Equipo`** | Se usa principalmente para clasificar y filtrar | Grafo más simple |
| `Fase` | nodo / propiedad | **Propiedad de `Partido`** | Describe la etapa del encuentro | Evita un nodo sin navegación necesaria |
| Participación | inferir por equipo / relación propia | **`PARTICIPA_EN`** | Pertenencia a un equipo no implica haber jugado | Permite consultas sobre participación real |
| Titularidad | propiedad del jugador / propiedad de relación | **Propiedad de `PARTICIPA_EN`** | Cambia entre partidos | Representa correctamente el contexto |
| Minutos jugados | propiedad de relación / módulo de estadísticas | **Fuera del grafo** | Es una métrica deportiva | Mantiene el alcance |
| Evento | propiedad del partido / nodo | **Nodo `Evento`** | Tiene identidad, propiedades y conexiones | Permite navegar acciones |
| Equipo del evento | relación directa / derivar por protagonista | **Derivar por `Jugador -> Equipo`** | Evita redundancia | Menos riesgo de inconsistencias |
| Sede | propiedad del partido / nodo | **Nodo `Sede`** | Es compartida por muchos partidos y aporta navegación | Habilita recorridos geográficos |
| Carga | `CREATE` / `MERGE` | **`MERGE`** | La carga debe ser idempotente | Re-ejecución controlada |
| Análisis RF9 | plugin GDS / funciones Cypher | **`shortestPath()` + conectividad** | Cubre el análisis con contenidos de la clase sin dependencia adicional | Entorno más simple |
