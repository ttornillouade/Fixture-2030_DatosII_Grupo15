from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status

from app import servicios
from app.esquemas import Sesion
from app.rutas.parametros import fuente, errores

router = APIRouter(tags=["Redis"], dependencies=[Depends(fuente("Redis"))])
SesionId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{8,64}$", description="Identificador de sesión")]


@router.get("/sesiones/{sesionId}", response_model=Sesion, responses=errores(400, 404, 503),
            summary="Obtiene una sesión activa")
def obtener_sesion(sesionId: SesionId):
    """404 si la sesión no existe o expiró; 503 si Redis no responde."""
    return servicios.sesion(sesionId)


@router.delete("/sesiones/{sesionId}", status_code=status.HTTP_204_NO_CONTENT,
               responses=errores(400, 404, 503), summary="Invalida una sesión")
def eliminar_sesion(sesionId: SesionId):
    servicios.eliminar_sesion(sesionId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
