# Ciclo de vida, expiración e invalidación

## Sesión

### Creación

La sesión se crea como `HASH` y recibe inmediatamente un TTL de 1800 segundos.

La creación usa `MULTI/EXEC` para que el estado y la expiración se apliquen como una unidad lógica en la demostración.

### Validación

La aplicación busca:

```text
fixture2030:session:{session_id}
```

Si la clave existe, utiliza sus atributos y verifica el estado de acceso.

### Renovación por actividad

Una actividad autenticada relevante actualiza:

```text
last_activity
```

y renueva el TTL a 1800 segundos.

Esto implementa una expiración deslizante por inactividad: la sesión no dura 30 minutos desde su creación, sino 30 minutos desde la última actividad renovadora.

No toda petición necesariamente debe renovar la sesión. La aplicación puede limitar la renovación a actividad significativa para evitar escrituras innecesarias.

### Expiración

Redis elimina la clave mediante su mecanismo nativo de TTL.

No existe un proceso que recorra todas las sesiones para detectar manualmente las vencidas.

### Cierre explícito

Logout o revocación:

```text
DEL fixture2030:session:{session_id}
```

### Sesión inexistente

Se interpreta como sesión inválida o vencida. La aplicación debe solicitar autenticación nuevamente.

Ante una caída de Redis, una sesión no puede considerarse válida solo porque el cliente posea un identificador. Para sesiones se adopta un comportamiento fail-closed.

---

# Caché de Equipo

Se utiliza cache-aside.

## HIT

```text
Cliente
  -> Redis
  -> dato encontrado
  -> respuesta
```

## MISS

```text
Cliente
  -> Redis
  -> clave ausente
  -> fuente de verdad (MongoDB / simulación local)
  -> respuesta
  -> HSET Redis
  -> EXPIRE 300
```

## Invalidación

El TTL de cinco minutos es un límite temporal, pero no es la única estrategia de coherencia.

Cuando una escritura de negocio modifica el equipo en la fuente de verdad:

1. primero se confirma la escritura persistente;
2. se ejecuta `DEL fixture2030:cache:equipo:{id}`;
3. la siguiente lectura produce MISS;
4. la caché se reconstruye desde la fuente actualizada.

Se elige invalidación en vez de actualizar simultáneamente la copia porque reduce el riesgo de que una escritura parcial deje Redis y MongoDB con valores distintos.

## Redis no disponible

Para datos cacheados, la aplicación puede omitir Redis y consultar directamente la fuente de verdad. El resultado será más lento, pero no se pierde integridad del dato persistente.

Esta decisión es diferente de las sesiones, donde Redis contiene el estado temporal necesario para validar el acceso.
