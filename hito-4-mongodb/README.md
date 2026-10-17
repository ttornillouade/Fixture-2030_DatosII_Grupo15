# Grupo 15 — Hito 4 — Módulo documental de equipos y jugadores (MongoDB)

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

Colecciones `equipos` (64) y `jugadores` (1.536) del Fixture 2030 en MongoDB, con validación,
carga idempotente, consultas, una agregación y un índice justificado con `explain()`.
El módulo guarda **solo atributos propios de cada entidad**: las métricas deportivas
(goles, asistencias, atajadas) pertenecen a su propio módulo.

Decisiones de diseño: [`docs/decisiones_documentales.md`](docs/decisiones_documentales.md).

## Estructura

```text
hito-4-mongodb/
├── docker-compose.yml          MongoDB + persistencia en ~/docker/data/mongodb
├── data/                       equipos.csv y jugadores.csv (los mismos del Hito 5)
├── scripts/
│   ├── 01_validacion.js        colecciones con $jsonSchema (RF7)
│   ├── 02_carga.js             carga idempotente con upsert (RF4, RF5, RF8)
│   ├── 03_operaciones.js       inserción, actualización y consultas (RF9, RF10)
│   ├── 04_agregacion.js        planteles por confederación y posición (RF11)
│   ├── 05_indices_rendimiento.js  índice principal con explain() antes y después (RF12, RF13)
│   ├── 06_integridad.js        volumen, relaciones y validación (RNF2, RNF3)
│   └── generar_evidencia.sh    ejecuta todo y guarda la salida
└── docs/
    ├── decisiones_documentales.md
    └── evidencia/
```

## Ejecución

Desde esta carpeta:

```bash
docker compose up -d
bash scripts/generar_evidencia.sh
```

La primera vez, o para repetir la evidencia desde una base vacía:
`bash scripts/generar_evidencia.sh --desde-cero` (borra solo la base `fixture2030` de la demo).

Cada script también se puede ejecutar por separado:

```bash
docker exec fixture2030-mongodb mongosh --quiet /scripts/05_indices_rendimiento.js
```

Para explorar con `mongosh`: `docker exec -it fixture2030-mongodb mongosh fixture2030`.

**Detener sin perder datos:** `docker compose down` (los datos quedan en `~/docker/data/mongodb`).
**Recargar:** `docker compose up -d` y `docker exec fixture2030-mongodb mongosh --quiet /scripts/02_carga.js`.

## Evidencia

[`docs/evidencia/`](docs/evidencia/): versión de MongoDB, carga de 64 equipos y 1.536 jugadores,
segunda carga sin cambios, operaciones, agregación, `explain()` antes y después del índice
(24 → 7 documentos examinados) e integridad sin jugadores huérfanos.

## Limitaciones

- Datos sintéticos, compartidos con el Hito 5 para que los ids coincidan entre módulos.
- Una sola instancia local, sin replica set (el diseño distribuido del Hito 3 queda conceptual).
- MongoDB no valida que `jugadores.equipoId` exista en `equipos`: lo controla `06_integridad.js`.
- Con 1.536 jugadores los tiempos absolutos son mínimos: el análisis se basa en documentos y
  claves examinados.
