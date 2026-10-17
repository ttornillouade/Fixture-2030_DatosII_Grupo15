# Evidencia del Hito 5

La evidencia debe provenir de una ejecución real del módulo.

## 1. Evidencia textual

Ejecutar:

```bash
bash scripts/generar_evidencia.sh
```

Se genera:

```text
docs/evidencia/salida_hito5.txt
```

## 2. Capturas a incorporar

1. `docker compose ps` con Neo4j activo.
2. Conteos: 64 equipos, 1.536 jugadores, 127 partidos, 6 sedes y 508 eventos.
3. Segunda ejecución de carga con los mismos conteos.
4. Consulta `Jugador -> Equipo -> Partido -> Sede`.
5. Consulta `Jugador -> Evento -> Partido -> Sede`.
6. Visualización de `queries/visualizacion.cypher`.
7. `SHOW CONSTRAINTS`.
8. `SHOW INDEXES`.
9. Un `PROFILE` de `queries/rendimiento.cypher`.

No se incluyen capturas ficticias en este paquete.
