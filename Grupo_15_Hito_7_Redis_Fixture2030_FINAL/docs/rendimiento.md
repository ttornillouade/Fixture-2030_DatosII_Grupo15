# Rendimiento — pendiente de ejecución

La consigna exige medir operaciones principales y documentar entorno, método y resultado real.

Se incluye:

```bash
bash scripts/prueba_rendimiento.sh
```

Por defecto ejecuta 50.000 operaciones con 50 clientes concurrentes para:

- `SET` con TTL;
- `GET`;
- `HSET`.

También registra:

- fecha;
- versión de Redis;
- recursos observados del contenedor;
- `INFO memory`.

No se declaran tasas antes de ejecutar la prueba.

## Concurrencia funcional

Separadamente:

```bash
bash scripts/prueba_concurrencia.sh 10000 50
```

realiza 10.000 `ZINCRBY` con 50 clientes concurrentes y luego comprueba el score final.

El objetivo de esa prueba no es solo throughput: demuestra que la actualización concurrente usa una operación atómica nativa y no pierde incrementos por una secuencia read-modify-write.

## Limitaciones

Los números obtenidos corresponderán a:

- un único nodo;
- Docker local;
- recursos de la notebook;
- loopback local;
- una carga sintética;
- ausencia de latencia de red productiva.

Por eso se interpretarán como evidencia reproducible del laboratorio y no como benchmark general de Redis.
