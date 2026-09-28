# Rendimiento y medición

La meta de 10.000 escrituras/s es un objetivo de prueba, no un resultado asumido.

`scripts/generar_volumen.py` crea 1.100.000 comentarios reproducibles. `scripts/carga_volumen.sh` registra fecha, versión, recursos observados, filas, tiempo y tasa aproximada.

```bash
bash scripts/carga_volumen.sh 1100000
```

Si no se alcanzan 10.000/s se entrega la tasa real, el método y las limitaciones. Factores a registrar: CPU/memoria Docker, disco local, nodo único, uso de `COPY FROM` y costo adicional de la tabla secundaria.
