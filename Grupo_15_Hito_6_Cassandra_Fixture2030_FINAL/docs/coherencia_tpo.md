# Coherencia con el TPO

- Hitos 1–2: comentarios como flujo masivo, de escritura intensiva y accesos conocidos.
- Hito 3: publicación/feed priorizan disponibilidad; moderación podría requerir consistencia más fuerte en una topología con réplicas. El laboratorio RF=1 no simula eso.
- Hito 4: se mantiene separación de responsabilidades; Cassandra no copia fichas completas de jugadores/equipos.
- Hito 5: `partido_id` reutiliza el contrato de identidad (`P001`) del nodo Partido en Neo4j.
