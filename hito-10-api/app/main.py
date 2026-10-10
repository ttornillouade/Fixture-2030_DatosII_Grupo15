"""API REST integrada del Fixture 2030: una ruta por caso de uso y un adaptador por base."""
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errores import ErrorApi
from app.rutas import comentarios, equipos, estadisticas, partidos, sesiones

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")

app = FastAPI(title="Fixture 2030 API", version="1.0.0",
              description="API REST que integra MongoDB, Neo4j, Cassandra, Redis, InfluxDB e IRIS. "
                          "Cada endpoint consulta una sola base, respetando su modelo de acceso.",
              servers=[{"url": "http://localhost:8000", "description": "API local (notebook)"}])
for modulo in (equipos, partidos, comentarios, sesiones, estadisticas):
    app.include_router(modulo.router)


@app.middleware("http")
async def correlacion(request: Request, call_next):
    """Asigna un requestId a cada request y registra método, ruta, estado y duración."""
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id
    inicio = time.perf_counter()
    respuesta = await call_next(request)
    respuesta.headers["X-Request-ID"] = request_id
    # No se registran cuerpos, query strings ni credenciales: solo lo necesario para correlacionar.
    log.info("%s %s fuente=%s status=%s %.0fms %s", request.method, request.url.path,
             getattr(request.state, "fuente", "-"), respuesta.status_code,
             (time.perf_counter() - inicio) * 1000, request_id)
    return respuesta


def _error(request: Request, status: int, code: str, message: str, **extra) -> JSONResponse:
    cuerpo = {"code": code, "message": message, "requestId": getattr(request.state, "request_id", None), **extra}
    return JSONResponse(status_code=status, content=cuerpo)


@app.exception_handler(ErrorApi)
async def error_api(request: Request, e: ErrorApi):
    return _error(request, e.status, e.code, e.message)


@app.exception_handler(RequestValidationError)
async def error_validacion(request: Request, e: RequestValidationError):
    campos = [{"campo": ".".join(str(p) for p in err["loc"][1:]), "detalle": err["msg"]} for err in e.errors()]
    return _error(request, 400, "VALIDATION_ERROR", "La request no cumple el contrato", campos=campos)


@app.exception_handler(Exception)
async def error_inesperado(request: Request, e: Exception):
    log.exception("Error no controlado (%s)", getattr(request.state, "request_id", "-"))
    return _error(request, 500, "INTERNAL_ERROR", "Error interno")


def _openapi():
    """La API responde 400 (no 422) ante validaciones: el contrato publicado lo refleja."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    esquema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes,
                          servers=app.servers)
    for operaciones in esquema["paths"].values():
        for operacion in operaciones.values():
            operacion.get("responses", {}).pop("422", None)
    for nombre in ("HTTPValidationError", "ValidationError"):
        esquema.get("components", {}).get("schemas", {}).pop(nombre, None)
    app.openapi_schema = esquema
    return esquema


app.openapi = _openapi
