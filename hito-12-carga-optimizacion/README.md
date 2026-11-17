# Grupo 15 — Hito 12 — Pruebas de carga y optimización del Fixture 2030

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

Prueba de carga reproducible del flujo **comentarios en vivo durante un partido** (API del Hito 10 →
Cassandra del Hito 6), con línea base, identificación del cuello de botella, dos optimizaciones medidas por
separado y juntas, validación de integridad de cada escritura, una proyección analítica (Data Mart) y la
comparación con una alternativa relacional.

## Resultado en una línea

Con 60 usuarios virtuales, el límite de la línea base era **el proceso de la API (90 % de un núcleo), no
Cassandra**. Una caché de 1 s en Redis para la primera página más 3 procesos de la API llevaron el flujo de
**163 a 273 req/s (+67 %)** y el p95 de **399 a 186 ms (−53 %)**, con 0 % de errores HTTP y las 11.485
escrituras verificadas. La validación encontró **una escritura fantasma** (POST con timeout del cliente que sí
se escribió) causada por el arranque en frío de un proceso: está documentada con su corrección propuesta.

| Medianas de 3 corridas | Línea base | Caché | 3 workers | Caché + 3 workers |
|---|---|---|---|---|
| Throughput (req/s) | 163,4 | 248,2 | 237,9 | **272,8** |
| p50 / p95 / p99 (ms) | 203 / 399 / 487 | 73 / 238 / 368 | 82 / 260 / 383 | **58 / 186 / 273** |
| CPU API · Cassandra · equipo | 90 % · 102 % · 79 % | 80 % · 72 % · 89 % | 145 % · 147 % · 98 % | 93 % · 69 % · 89 % |

Todas las cifras son mediciones del laboratorio (una PC con 6 núcleos); no son una garantía de producción.
Ver `docs/integridad_y_limitaciones.md`.

## Documentación

| Apartado (sección 8 de la consigna) | Documento |
|---|---|
| Flujo seleccionado, escenario de carga, método de medición | [docs/flujo_y_escenario_de_carga.md](docs/flujo_y_escenario_de_carga.md) |
| Datos de prueba | [datos-o-generadores/README.md](datos-o-generadores/README.md) |
| Entorno (hardware, versiones, diferencias en Windows) | [compose-o-instrucciones-del-entorno.md](compose-o-instrucciones-del-entorno.md) |
| Línea base | [docs/linea_base.md](docs/linea_base.md) |
| Hipótesis de cuello de botella, optimización, repetición y comparación | [docs/hipotesis_y_optimizacion.md](docs/hipotesis_y_optimizacion.md) |
| Tablas y gráficos antes/después (generados) | [docs/evidencia/comparacion.md](docs/evidencia/comparacion.md) |
| Integridad, limitaciones y extrapolación | [docs/integridad_y_limitaciones.md](docs/integridad_y_limitaciones.md) |
| Data Mart | [docs/integracion_data_mart.md](docs/integracion_data_mart.md) |
| Alternativa relacional | [docs/comparacion_relacional.md](docs/comparacion_relacional.md) |
| Evidencia de cada corrida | [docs/evidencia/](docs/evidencia/) |

## Estructura

```text
hito-12-carga-optimizacion/
├── README.md
├── compose-o-instrucciones-del-entorno.md
├── requirements.txt                 herramientas del hito (generador, medición, gráficos)
├── config/
│   ├── escenario.json               escenario de carga (60 VU, 15+30+120 s, 75/15/10 %)
│   ├── escenario_demo.json          tráfico liviano para la demo del Hito 13 (no es una prueba)
│   ├── compose.volumenes-docker.yaml override de volúmenes para Windows
│   └── .gitignore                   logs y PID de la API de cada corrida
├── scripts/
│   ├── preparar_datos.py            PREPARACIÓN: 200.000 comentarios sintéticos en P901-P904
│   ├── ejecutar_linea_base.sh       LÍNEA BASE: 3 corridas con la API original
│   ├── ejecutar_prueba_optimizada.sh OPTIMIZADA: caché / workers / ambos, 3 corridas cada uno
│   ├── correr_escenario.sh          una corrida: API → carga → log del servidor → integridad
│   ├── ejecutar_carga.py            CARGA Y MEDICIÓN: generador multiproceso + recursos
│   ├── analizar_log_api.py          MEDICIÓN del lado del servidor
│   ├── validar_integridad.py        VALIDACIÓN de cada escritura, duplicados, fantasmas y caché
│   ├── comparar_resultados.py       COMPARACIÓN: tablas y gráficos
│   ├── data_mart_etl.py             DATA MART: carga, validación y comparación fuente vs proyección
│   ├── limpiar_datos_de_prueba.py   LIMPIEZA OPCIONAL (solo P901-P904 y U9xxxxx)
│   ├── api_lab.py                   inicia/detiene la API con la configuración de cada corrida
│   └── comun.py                     constantes compartidas (partidos y usuarios de laboratorio)
├── docs/ ... y docs/evidencia/      análisis y resultados de cada corrida
└── datos-o-generadores/README.md
```

Los cambios en la API para la optimización están en `hito-10-api/` (caché en
`app/adaptadores/cache_comentarios.py`, uso en `app/servicios.py`, `API_WORKERS` en `scripts/iniciar_api.sh`).
Con la configuración por defecto (`CACHE_COMENTARIOS_TTL_MS=0`, 1 proceso) la API se comporta igual que en
el Hito 10.

## Requisitos

- Docker Desktop, Python 3.11 o 3.12, Git Bash (en Windows).
- Las seis bases del Hito 10 con sus datos y el entorno virtual de la API (`hito-10-api/.venv`, `.env`).
- La API **no** debe estar corriendo: cada corrida la inicia y la detiene con su propia configuración.
- Recursos: la prueba ocupa ~80 % de una CPU de 6 núcleos durante ~3 minutos por corrida. No ejecutar otras
  tareas pesadas en paralelo (una descarga de imágenes de Docker invalidó una corrida: ver evidencia).

## Preparación (una vez)

```bash
cd hito-10-api && cp .env.example .env
```

```bash
cd hito-10-api && docker compose -f compose.yaml -f ../hito-12-carga-optimizacion/config/compose.volumenes-docker.yaml up -d --wait && bash scripts/inicializar_datos.sh
```

```bash
cd hito-12-carga-optimizacion && python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cd hito-12-carga-optimizacion && .venv/bin/python scripts/preparar_datos.py --total 200000 --horas 3
```

1. Definir `NEO4J_PASSWORD` e `IRIS_PASSWORD` en `.env` (valores locales, no se versionan).
2. Bases + datos de los hitos anteriores. En macOS/Linux alcanza con `bash scripts/levantar_todo.sh`; el
   override de volúmenes es para Windows (ver `compose-o-instrucciones-del-entorno.md`, también para IRIS y
   el venv en Windows).
3. Entorno de las herramientas del hito (en Windows: `.venv\Scripts`; ver el mismo documento).
4. Historial de comentarios de laboratorio (~2 min). Deja `docs/evidencia/datos_preparados.json`.

## Orden de ejecución

```bash
cd hito-12-carga-optimizacion && bash scripts/ejecutar_linea_base.sh
```

```bash
cd hito-12-carga-optimizacion && bash scripts/ejecutar_prueba_optimizada.sh todas
```

```bash
cd hito-12-carga-optimizacion && .venv/bin/python scripts/comparar_resultados.py linea_base optimizada_cache optimizada_workers optimizada_cache_workers
```

```bash
cd hito-12-carga-optimizacion && .venv/bin/python scripts/data_mart_etl.py cargar && .venv/bin/python scripts/data_mart_etl.py validar && .venv/bin/python scripts/data_mart_etl.py comparar
```

1. Línea base: 3 corridas (~10 min). Cada una deja `docs/evidencia/linea_base_rN_<fecha>/`.
2. Las tres configuraciones optimizadas, 3 corridas cada una (~32 min). Una sola: `cache`, `workers` o `cache_workers`.
3. Tablas y gráficos antes/después en `docs/evidencia/comparacion*.{md,png}`.
4. Proyección analítica, su validación y la comparación con la fuente operacional.

`REPETICIONES=1 bash scripts/ejecutar_linea_base.sh` hace una sola corrida. Ctrl+C corta la carga y guarda
lo medido.

## Limpieza segura

```bash
cd hito-12-carga-optimizacion && .venv/bin/python scripts/limpiar_datos_de_prueba.py
```

```bash
cd hito-12-carga-optimizacion && .venv/bin/python scripts/limpiar_datos_de_prueba.py --confirmar --mart
```

1. Simulación: muestra qué particiones borraría.
2. Borra solo los comentarios de P901-P904, los de los usuarios U900000-U909999, el keyspace del Data Mart y
   las claves de caché de P90x. No toca los datos de los Hitos 4-11, ni volúmenes, ni la evidencia.
