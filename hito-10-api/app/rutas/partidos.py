from fastapi import APIRouter, Depends

from app import servicios
from app.esquemas import CambioEstado, PartidoDetalle
from app.rutas.parametros import PartidoCodigo, errores, fuente

router = APIRouter(tags=["IRIS"], dependencies=[Depends(fuente("IRIS"))])


@router.get("/partidos/{codigo}/detalle", response_model=PartidoDetalle, responses=errores(400, 404, 503, 504),
            summary="Detalle del partido con sus eventos (entidad compleja)")
def detalle(codigo: PartidoCodigo):
    return servicios.detalle(codigo)


@router.patch("/partidos/{codigo}/estado", response_model=PartidoDetalle, responses=errores(400, 404, 409, 503, 504),
              summary="Transición validada del estado del partido")
def cambiar_estado(codigo: PartidoCodigo, cambio: CambioEstado):
    """PROGRAMADO -> EN_JUEGO -> FINALIZADO. Es un update condicionado al estado de origen:
    una transición ilegal, o repetida, devuelve 409 sin modificar el partido."""
    return servicios.cambiar_estado(codigo, cambio.estado)
