# Coherencia con el TPO

## Hitos 1–2

Redis había sido seleccionado para sesiones por el patrón clave/valor, la necesidad de baja latencia y la naturaleza temporal del estado.

## Hito 3

La arquitectura distribuida diferenciaba el estado de sesión de otros datos persistentes. En este hito la validez de la sesión se controla mediante TTL e invalidación explícita.

## Hito 4

MongoDB continúa siendo la fuente de verdad de `Equipo` y `Jugador`.

El caché:

```text
fixture2030:cache:equipo:E001
```

es únicamente una copia de acceso rápido y puede reconstruirse.

## Hito 5

Los IDs `P001`, `P002`, etc. utilizados en rankings temporales mantienen la misma identidad semántica que los nodos `Partido` de Neo4j.

## Hito 6

Cassandra continúa siendo responsable de comentarios masivos. Redis no absorbe comentarios ni reemplaza su almacenamiento.

La regla de arquitectura se mantiene:

> Cada tecnología conserva la responsabilidad para la cual fue seleccionada; Redis almacena estado transitorio y copias reconstruibles.
