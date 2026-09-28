# Patrones de acceso

El esquema se define desde las consultas prioritarias, no desde un DER.

| Patrón | Parámetros conocidos | Orden/límite | Frecuencia |
|---|---|---|---|
| Publicar comentario | partido, autor, instante, contenido | — | muy alta |
| Feed reciente de partido | partido + bucket + shards | creado_en DESC, 20–100 | muy alta |
| Moderar comentario | PK completa | fila única | media |
| Eliminar comentario | PK completa | fila única | baja |
| Historial de usuario | autor + día | creado_en DESC, 20–100 | media |

El feed consulta 8 particiones del bucket actual y fusiona resultados. Si faltan filas, consulta el bucket anterior. Esto agrega fan-out de lectura a cambio de repartir escrituras.

El historial por usuario se resuelve con una segunda tabla. No se usa `ALLOW FILTERING`.
