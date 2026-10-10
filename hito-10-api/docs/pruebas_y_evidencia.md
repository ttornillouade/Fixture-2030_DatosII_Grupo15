# Pruebas y evidencia

## Cómo se prueba

Con la API corriendo (`bash scripts/iniciar_api.sh`):

```bash
bash scripts/ejecutar_pruebas.sh
```

Guarda la salida en `docs/evidencia/pruebas_<fecha>.txt` y ejecuta:

1. **Conectividad** de las seis bases con su cliente nativo.
2. **Contrato:** `openapi/openapi.yaml` coincide con las rutas implementadas.
3. **Colección Bruno** (`bruno/`): 32 requests con tests de estado y de contenido.
4. **Contraste:** la respuesta de la API junto a la misma consulta hecha con el cliente nativo (RF17).
5. **Dependencia caída:** se detiene Neo4j (sus datos están en un volumen), se pide el endpoint y se
   vuelve a levantar.
6. **Latencia básica.**

La colección también se puede abrir en la app de Bruno (carpeta `bruno/`, entorno `local`).

## Cobertura (punto 5.12 de la consigna)

| Escenario | Dónde |
|---|---|
| Request válida por módulo | `01-mongodb` a `06-iris` |
| Parámetro inválido (400) | `equipo-codigo-invalido`, `plantel-sin-equipo`, `eventos-codigo-invalido`, `sin-bucket`, `bucket-desalineado`, `crear-vacio`, `ventana-excedida`, `rango-invertido`, `estado-invalido` |
| Recurso inexistente (404) | `equipo-inexistente`, `eventos-inexistente`, `iris/inexistente` |
| Respuesta vacía válida (200) | `plantel-vacio` (MongoDB), `ventana-sin-puntos` (InfluxDB) |
| Sesión ausente o expirada (404) | `04-redis/obtener-eliminada` |
| Conflicto (409) | `06-iris/iniciar-de-nuevo` |
| Escritura repetida | `03-cassandra/crear-repetido`: el segundo POST crea otro `comentarioId` |
| Paginación y ventanas | `plantel` → `plantel-siguiente`, `pagina` → `siguiente-pagina`, `ventana-excedida` |
| Dependencia detenida (503) | Sección 5 de `ejecutar_pruebas.sh` |
| Documentación = respuesta real | Sección 2 (contrato) y los tests de Bruno |

Efectos de la colección: crea 2 comentarios por corrida, crea e invalida una sesión y lleva P003 a
`FINALIZADO` (`preparar_datos_demo.sh` lo vuelve a `PROGRAMADO`).

## Resultados (docs/evidencia/)

- Conectividad: las 6 bases OK.
- Bruno: 32/32 requests, 36/36 tests.
- Dependencia caída: con Neo4j detenido, `GET /partidos/P001/eventos` responde 503 inmediato
  (conexión rechazada) mientras `GET /equipos/E010` sigue en 200; al volver Neo4j, 200 sin reiniciar la API.
  Si la base no responde (en lugar de rechazar), el límite es `TIMEOUT_S` = 3 s.

## Rendimiento básico

- **Método:** 20 requests secuenciales por endpoint con `curl` (`time_total`); se informa mediana,
  p95 y máximo.
- **Entorno:** API (uvicorn, 1 proceso) y bases en la misma notebook (Apple M5, 16 GB, Docker Desktop).
- **Volumen:** 64 equipos y 1.536 jugadores (MongoDB), 127 partidos y 508 eventos (Neo4j), comentarios
  del Hito 6, puntos de un partido del Hito 8.
- **Resultado:** ver la sección 6 de la evidencia (medianas de 1 a 6 ms).
- **Limitaciones:** sin concurrencia, sin red real entre API y bases, un solo nodo por base y datos en
  caché. Mide la sobrecarga de la API y el adaptador, no la capacidad del sistema: no permite afirmar
  nada sobre miles de usuarios simultáneos.

## Coherencia con el TPO

| Hito | Base | Endpoint que la usa |
|---|---|---|
| 4 | MongoDB | `/equipos/{codigo}`, `/jugadores` |
| 5 | Neo4j | `/partidos/{codigo}/eventos` |
| 6 | Cassandra | `/partidos/{codigo}/comentarios` |
| 7 | Redis | `/sesiones` |
| 8 | InfluxDB | `/partidos/{codigo}/estadisticas` |
| 9 | IRIS | `/partidos/{codigo}/detalle`, `/partidos/{codigo}/estado` |

Los identificadores son compartidos (`E010`, `E001-J09`, `P001`), pero cada base conserva su rol:
la API no copia datos entre bases ni combina fuentes en una respuesta. Diferencia de formato: IRIS
identifica jugadores como `E001J09` y los demás módulos como `E001-J09`.
