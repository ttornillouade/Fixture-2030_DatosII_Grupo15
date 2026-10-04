# Grupo 15 — Hito 8 — Series temporales de estadísticas en vivo (InfluxDB)

**Repositorio GitHub:** https://github.com/ttornillouade/Fixture-2030_DatosII_Grupo15

Módulo de series temporales del Fixture 2030: registra estadísticas de partido, rendimiento
físico de jugadores, eventos y actividad de la plataforma; permite consultar ventanas,
comparar dimensiones, agregar con la función correcta según la semántica de cada medida
y conservar historia resumida con una política de retención explícita.

## Decisiones principales

```text
Motor:       InfluxDB 3 Core (imagen influxdb:3-core), SQL sobre Parquet, puerto 8181
Precisión:   milisegundos (precision=millisecond en todas las escrituras)

Bases:
  fixture2030_vivo        retención 14d   datos originales (1 Hz / ms)
  fixture2030_historico   retención none  resúmenes de 1 minuto (downsampling)

Tablas (vivo):
  estadisticas_equipo   tags partido_id, equipo_id, condicion, fase, sede_id, pais_sede   1 pt/s/equipo
  rendimiento_jugador   tags partido_id, equipo_id, jugador_id                           1 pt/s/jugador
  eventos_partido       tags partido_id, equipo_id, tipo_evento                          irregular
  actividad_usuarios    tags partido_id, plataforma, fase, pais_sede                     1 pt/s/plataforma

Series estimadas para 104 partidos: 4.937  (sin user_id, session_id ni ids de evento como tags)
Volumen proyectado del torneo: ~17,3 M puntos (166 mil por partido)
```

## Estructura

```text
hito-8-influxdb/
├── docker-compose.yml          servicio influxdb:3-core + ~/docker/data/influxdb
├── .env.example                configuración local (el .env real no se versiona)
├── .gitignore
├── README.md                   esta guía
├── Hito8.md                    resumen del análisis y de las decisiones
├── scripts/
│   ├── comun.sh                variables y funciones comunes
│   ├── inicializacion.sh       levanta el contenedor y verifica el servidor (RF1)
│   ├── autorizacion.sh         crea el token de admin y lo guarda solo en .env
│   ├── crear_bases.sh          bases + retención (RF10)
│   ├── generacion_puntos.py    genera line protocol reproducible (RF7)
│   ├── carga_lotes.py          carga por lotes, concurrencia, reintentos (RF7, RF12)
│   ├── validacion.py           conteos, series, distribución 1 Hz, tipos (RF7, RF11)
│   ├── consultar.py            ejecuta los .sql con rango acotado y mide tiempos
│   ├── consultas_temporales.sh RF8
│   ├── agregaciones.sh         RF9
│   ├── downsampling.sh/.py     resumen 1 min vivo -> histórico (RF10)
│   ├── caches_ultimo_valor.sh  Last Value Cache para el estado en vivo
│   ├── simulador_vivo.py       partido "en curso" para la ventana con now()
│   ├── ambiente.sh             fecha, CPU, RAM, Docker, versión de InfluxDB
│   ├── prueba_rendimiento.sh   medición de carga y consultas (RF13)
│   ├── generar_evidencia.sh    corrida completa con salida a docs/evidencia (RF14)
│   ├── limpieza.sh             limpieza opcional (con confirmación)
│   └── influx_comun.py         cliente HTTP y utilidades compartidas
├── sql/
│   ├── consultas/              c01..c09 (ventanas, filtros, comparaciones, vivo, ausencia)
│   └── agregaciones/           a01..a07 (avg/last, max+delta, count, sum, histórico)
├── data/generated/             salida del generador (ignorada por git)
└── docs/
    ├── problema_temporal.md
    ├── patrones_de_acceso.md
    ├── modelo_multidimensional.md
    ├── cardinalidad_y_escalabilidad.md
    ├── carga_de_datos.md
    ├── consultas_y_agregaciones.md
    ├── retencion_y_granularidad.md
    ├── seguridad_local.md
    ├── pruebas_y_evidencia.md
    ├── coherencia_tpo.md
    ├── checklist_requisitos.md
    └── evidencia/
```

## Requisitos

- Docker Desktop (o Docker Engine) con `docker compose`.
- Python 3.9 o superior (solo librería estándar, sin `pip install`).
- `curl` (viene con macOS y con la mayoría de las distribuciones Linux).

Todos los comandos se ejecutan desde esta carpeta (`hito-8-influxdb/`).

## 1. Preparar

```bash
cp .env.example .env
docker compose config        # valida el compose y muestra las variables resueltas
```

## 2. Levantar InfluxDB y verificar

```bash
bash scripts/inicializacion.sh
```

Crea `~/docker/data/influxdb`, ejecuta `docker compose up -d`, espera al puerto 8181 y
muestra la versión con el CLI del contenedor (`influxdb3 --version`).

Comprobar el estado en cualquier momento:

```bash
docker compose ps
docker compose logs --tail 50 influxdb
```

## 3. Autorización local

```bash
bash scripts/autorizacion.sh
```

Ejecuta `influxdb3 create token --admin` dentro del contenedor y escribe el token en
`.env` (`INFLUX_TOKEN=...`). El token no se imprime completo y `.env` está en `.gitignore`.

## 4. Crear bases con retención

```bash
bash scripts/crear_bases.sh
```

## 5. Generar puntos

```bash
python3 scripts/generacion_puntos.py --perfil demo     # 2 partidos,  ~0,33 M puntos
python3 scripts/generacion_puntos.py --perfil lab      # 12 partidos, ~2 M puntos
python3 scripts/generacion_puntos.py --perfil torneo   # 104 partidos, ~17,3 M puntos (~300 MB gz)
```

La generación es determinística (`--semilla 2030`). Por defecto, el calendario se ancla a
las últimas horas para que los datos queden dentro de la retención de 14 días.

## 6. Cargar

```bash
python3 scripts/carga_lotes.py                       # lote 5000, 4 hilos
python3 scripts/carga_lotes.py --lote 10000 --hilos 8
python3 scripts/carga_lotes.py --demo-errores        # muestra el rechazo parcial de líneas
```

## 7. Validar

```bash
python3 scripts/validacion.py
```

Compara puntos, series, distribución por minuto, coherencia entre tablas y tipos contra el
manifiesto de la generación. Termina con `VALIDACION OK` o con la lista de diferencias.

## 8. Consultas y agregaciones

```bash
bash scripts/consultas_temporales.sh
bash scripts/agregaciones.sh
python3 scripts/consultar.py sql/consultas/c03_comparacion_equipos.sql   # una sola
```

O directamente con el CLI del contenedor:

```bash
set -a; . ./.env; set +a
INFLUXDB3_AUTH_TOKEN="$INFLUX_TOKEN" docker exec -e INFLUXDB3_AUTH_TOKEN fixture2030-influxdb \
  influxdb3 query --database fixture2030_vivo \
  "SELECT tipo_evento, count(*) FROM eventos_partido WHERE time >= now() - INTERVAL '1 day' GROUP BY 1"
```

## 9. Retención y downsampling

```bash
bash scripts/downsampling.sh                         # vivo (1 s) -> histórico (1 min)
python3 scripts/consultar.py sql/agregaciones/a07_historico_1m.sql
```

## 10. Estado en vivo (opcional)

```bash
bash scripts/caches_ultimo_valor.sh
python3 scripts/simulador_vivo.py --segundos 90 --corte 30:20 &
python3 scripts/consultar.py sql/consultas/c06_ventana_reciente.sql sql/consultas/c07_ultimo_valor_cache.sql
```

## 11. Evidencia y rendimiento

```bash
bash scripts/generar_evidencia.sh demo               # corrida completa -> docs/evidencia/evidencia_hito8_*.txt
bash scripts/prueba_rendimiento.sh lab 5000 4 5      # RF13 -> docs/evidencia/rendimiento_hito8_*.txt
BARRIDO="1000x1 5000x4 10000x8" bash scripts/prueba_rendimiento.sh lab
```

Los tokens se enmascaran automáticamente en toda la evidencia.

## 12. Detener y reiniciar sin perder datos

```bash
docker compose down
docker compose up -d
python3 scripts/validacion.py        # los mismos conteos que antes del reinicio
```

Los datos, el catálogo y los tokens viven en `~/docker/data/influxdb` (montado en
`/var/lib/influxdb3`). No cambiar `INFLUX_NODE_ID` entre reinicios.

## 13. Limpieza opcional

```bash
bash scripts/limpieza.sh --datos-generados   # borra data/generated
bash scripts/limpieza.sh --bases             # borra las dos bases (pide confirmación)
bash scripts/limpieza.sh --reset-total       # baja el contenedor e indica cómo borrar el volumen
```

## Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| El contenedor se reinicia con `exec: influxdb3: not found` | Se está usando la imagen `influxdb:latest`, que en Docker Hub es InfluxDB 2.x. Usar `influxdb:3-core` como en el `docker-compose.yml` de esta carpeta. |
| El contenedor se reinicia y los logs piden `--node-id` u `--object-store` | Se está usando un compose de InfluxDB 2. Usar el `docker-compose.yml` de esta carpeta. |
| `autorizacion.sh` no puede crear el token | Ya existe un token de admin en el volumen. Pegarlo en `.env` o, si se perdió, `limpieza.sh --reset-total` y borrar `~/docker/data/influxdb`. |
| `Permission denied` en `/var/lib/influxdb3` (Linux) | El proceso del contenedor corre como usuario no root. Ver su UID con `docker run --rm --entrypoint id influxdb:3-core` y aplicar `sudo chown -R <uid>:<gid> ~/docker/data/influxdb` (en macOS con Docker Desktop no suele hacer falta). |
| HTTP 401 en la carga o en las consultas | `INFLUX_TOKEN` vacío o de otra instancia: volver a ejecutar `autorizacion.sh`. |
| Una consulta sobre todo el torneo falla por cantidad de archivos | InfluxDB 3 Core limita la cantidad de archivos Parquet que lee una consulta. Acotar el rango temporal o el partido (ver `docs/cardinalidad_y_escalabilidad.md`). |
| `--retention-period` no reconocido | Versión anterior de Core: `crear_bases.sh` crea la base sin retención y lo informa. Registrar la versión observada. |
