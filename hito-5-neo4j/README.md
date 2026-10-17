# Grupo 15 — Hito 5 — Módulo de Grafos del Fixture 2030

Implementación del módulo relacional del Fixture 2030 con Neo4j.

## Modelo

```text
Jugador -[:PERTENECE_A]-> Equipo
Jugador -[:PARTICIPA_EN {titular}]-> Partido
Equipo -[:DISPUTA {rol}]-> Partido
Partido -[:SE_JUEGA_EN]-> Sede
Jugador -[:PROTAGONIZA]-> Evento
Evento -[:OCURRE_EN]-> Partido
```

`Equipo.grupo` y `Partido.fase` son propiedades.  
`Jugador` contiene únicamente atributos propios de la entidad; no se almacenan estadísticas deportivas.

## Volumen

- 64 equipos
- 1.536 jugadores
- 127 partidos
- 6 sedes
- 508 eventos
- 4572 participaciones

## Estructura

```text
Grupo_15_Hito_5_Neo4j_Fixture2030_FINAL/
├── docker-compose.yml
├── .env.example
├── import/
├── queries/
│   ├── estructura.cypher
│   ├── carga.cypher
│   ├── crud.cypher
│   ├── consultas_grafo.cypher
│   ├── analisis_relacional.cypher
│   ├── rendimiento.cypher
│   ├── integridad.cypher
│   └── visualizacion.cypher
├── scripts/
│   ├── load.sh
│   ├── run_all.sh
│   └── generar_evidencia.sh
└── docs/
    ├── modelo_grafo.md
    ├── decisiones.md
    ├── checklist_requisitos.md
    └── evidencia/
```

## Inicio

```bash
cp .env.example .env
docker compose up -d
docker compose ps
```

Neo4j Browser:

```text
http://localhost:7474
```

Bolt:

```text
neo4j://localhost:7687
```

## Carga

```bash
bash scripts/load.sh
```

La carga utiliza `MERGE`, por lo que puede repetirse sin generar duplicados.

## Consultas

```bash
bash scripts/run_all.sh
```

## Evidencia

```bash
bash scripts/generar_evidencia.sh
```

Luego incorporar las capturas indicadas en `docs/evidencia/README.md`.

## Persistencia

```bash
docker compose down
docker compose up -d
```

Los datos y logs permanecen en volúmenes nombrados.

Para eliminar intencionalmente el ambiente completo:

```bash
docker compose down -v
```

## `neo4j:latest`

La consigna exige `neo4j:latest`. Antes de entregar registrar en la evidencia:

- fecha de prueba;
- Image ID utilizada;
- cualquier observación de compatibilidad.
