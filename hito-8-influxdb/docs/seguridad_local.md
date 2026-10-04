# Seguridad local

| Elemento | Tratamiento |
|---|---|
| Token de administrador | Se crea con `influxdb3 create token --admin` (`autorizacion.sh`) y se guarda solo en `.env` con permisos 600. Nunca se imprime completo. |
| `.env` | En `.gitignore`. El repositorio solo tiene `.env.example`, con `INFLUX_TOKEN=` vacío. |
| Uso del token en el CLI | Se pasa como variable de entorno (`INFLUXDB3_AUTH_TOKEN`) a `docker exec`, no como argumento visible. |
| Uso del token en Python | Header `Authorization: Bearer ...`, leído de `.env` o del entorno. |
| Evidencia | `generar_evidencia.sh` y `prueba_rendimiento.sh` pasan toda la salida por `enmascarar` (`apiv3_****OCULTO****`). |
| Datos generados | `data/generated/` en `.gitignore` (se reconstruyen con la semilla). |
| Credenciales de InfluxDB 2 | No se usan. Las variables `DOCKER_INFLUXDB_INIT_USERNAME/PASSWORD` del compose anterior se eliminaron: InfluxDB 3 no tiene usuario/contraseña de setup. |
| Datos personales | No hay. Usuarios agregados por plataforma; sin user_id, IPs ni nombres reales. |

Antes de cada commit:

```bash
git status --ignored            # .env y data/generated deben figurar como ignorados
grep -rn "apiv3_" --include="*" . | grep -v "apiv3_\*\*\*\*" | grep -v "\.env$" || echo "sin tokens"
```

Si un token llegara a publicarse: rotarlo (`influxdb3 create token --admin --regenerate`) y reescribir el historial del repositorio.
