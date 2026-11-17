# Comparación antes / después (generado por scripts/comparar_resultados.py)

Valores: **mediana entre repeticiones** y, entre paréntesis, mínimo–máximo. Métricas del período de sostenimiento (120 s, 60 VU). Latencia = tiempo de respuesta HTTP visto por el generador, en ms. Latencia del servidor = duración registrada por la API para las lecturas de comentarios. CPU en % de un núcleo (100 = 1 núcleo), media de muestras cada 2 s.

| Métrica | Línea base | Opt. 1: caché Redis | Opt. 2 sola: 3 workers | Opt. 1+2: caché + 3 workers |
|---|---|---|---|---|
| Repeticiones | 3 | 3 | 3 | 3 |
| Throughput (req/s) | 163.4 (162.8–163.6) | 248.2 (225.7–256.5) | 237.9 (235.4–243.5) | 272.8 (267.5–273.7) |
| Requests en el sostenimiento | 19612 (19541–19626) | 29786 (27087–30778) | 28551 (28251–29224) | 32741 (32096–32848) |
| Latencia p50 (ms) | 203.4 (203.4–206.6) | 73.2 (69.6–87.5) | 81.8 (77.1–82.1) | 57.6 (53.5–57.8) |
| Latencia p95 (ms) | 398.8 (390.8–399.5) | 237.8 (218.9–304.5) | 260.1 (241.3–268.6) | 185.8 (171.7–197.4) |
| Latencia p99 (ms) | 487.1 (485.7–517.0) | 368.2 (326.0–494.1) | 382.9 (362.3–397.1) | 272.7 (250.4–316.8) |
| Latencia máxima (ms) | 834.6 (743.7–920.0) | 981.7 (740.9–2006.7) | 949.5 (801.2–1197.8) | 5167.9 (561.4–9235.8) |
| Tasa de error (%) | 0.00 | 0.00 | 0.00 (0.00–0.00) | 0.00 (0.00–0.01) |
| Servidor: lectura p50 (ms) | 140.0 (139.0–141.0) | 13.0 (12.0–15.0) | 28.0 (27.0–30.0) | 5.0 (4.0–5.0) |
| Servidor: lectura p95 (ms) | 303.0 (301.0–307.0) | 102.0 (97.0–137.0) | 85.0 (75.0–96.0) | 33.0 (30.0–39.0) |
| CPU API (% de 1 núcleo) | 90 (89–91) | 80 (77–82) | 145 (145–148) | 93 (92–94) |
| Memoria API (MB) | 174 (173–176) | 137 (136–137) | 430 (429–430) | 397 (396–400) |
| CPU Cassandra (%) | 102 (90–102) | 72 (64–73) | 147 (146–150) | 69 (68–70) |
| CPU Redis (%) | 1 (1–1) | 4 (4–5) | 2 (2–2) | 5 (5–5) |
| CPU generador (%) | 103 (101–104) | 203 (198–206) | 187 (186–190) | 208 (207–210) |
| CPU total del SO (% del equipo) | 79 (79–80) | 89 (87–92) | 98 (98–98) | 89 (89–91) |
| Integridad OK en todas las corridas | sí | sí | sí | **NO** |
| Escrituras verificadas (suma) | 7164 | 10339 | 10304 | 11485 |
| Commit | f09df39 | 5817539 | 5817539 | 5817539 |

## Variación respecto de la línea base (medianas)

| Configuración | Throughput | p50 | p95 | p99 | CPU API | CPU Cassandra |
|---|---|---|---|---|---|---|
| Opt. 1: caché Redis | +52 % | -64 % | -40 % | -24 % | -12 % | -29 % |
| Opt. 2 sola: 3 workers | +46 % | -60 % | -35 % | -21 % | +61 % | +44 % |
| Opt. 1+2: caché + 3 workers | +67 % | -72 % | -53 % | -44 % | +3 % | -33 % |

## Corridas incluidas

- linea_base: `linea_base_r1_20261113T165018Z`, `linea_base_r2_20261113T165324Z`, `linea_base_r3_20261113T165628Z`
- optimizada_cache: `optimizada_cache_r1_20261113T170045Z`, `optimizada_cache_r2_20261113T170353Z`, `optimizada_cache_r3_20261113T170659Z`
- optimizada_workers: `optimizada_workers_r1_20261113T171007Z`, `optimizada_workers_r2_20261113T171312Z`, `optimizada_workers_r3_20261113T171618Z`
- optimizada_cache_workers: `optimizada_cache_workers_r1_20261113T171923Z`, `optimizada_cache_workers_r2_20261113T172230Z`, `optimizada_cache_workers_r3_20261113T172536Z`
