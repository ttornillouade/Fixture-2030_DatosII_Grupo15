from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app import servicios
from app.esquemas import PartidosDeJugador
from app.rutas.parametros import errores, fuente

router = APIRouter(tags=["Neo4j"], dependencies=[Depends(fuente("Neo4j"))])
JugadorCodigo = Annotated[str, Path(pattern=r"^E[0-9]{3}-J[0-9]{2}$", description="Código de jugador",
                                    examples=["E001-J09"])]


@router.get("/jugadores/{codigo}/partidos", response_model=PartidosDeJugador, responses=errores(400, 404, 503, 504),
            summary="Partidos que jugó un jugador y contra qué rival (recorrido del grafo)")
def partidos_de_jugador(codigo: JugadorCodigo):
    return servicios.partidos_de_jugador(codigo)
