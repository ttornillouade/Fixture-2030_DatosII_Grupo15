from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app import servicios
from app.esquemas import Comentario, ComentarioEntrada, PaginaComentarios
from app.rutas.parametros import fuente, PartidoCodigo, errores

router = APIRouter(tags=["Cassandra"], dependencies=[Depends(fuente("Cassandra"))])


@router.get("/partidos/{codigo}/comentarios", response_model=PaginaComentarios, responses=errores(400, 503),
            summary="Página de comentarios de un partido en una ventana de 5 minutos")
def listar_comentarios(codigo: PartidoCodigo,
                       bucket: Annotated[datetime, Query(description="Inicio de la ventana de 5 minutos (partición)",
                                                          examples=["2030-06-08T20:00:00Z"])],
                       limit: Annotated[int, Query(ge=1, le=100)] = 20,
                       cursor: Annotated[str | None, Query(description="nextCursor de la página anterior")] = None):
    """Lee los 8 shards del bucket (clave de partición completa) y los fusiona por fecha descendente."""
    return servicios.comentarios(codigo, bucket, limit, cursor)


@router.post("/partidos/{codigo}/comentarios", response_model=Comentario, status_code=status.HTTP_201_CREATED,
             responses=errores(400, 503), summary="Agrega un comentario a un partido")
def crear_comentario(codigo: PartidoCodigo, entrada: ComentarioEntrada):
    """No es idempotente: cada request crea un comentario nuevo con id y fecha generados por el servidor."""
    return servicios.crear_comentario(codigo, entrada.usuarioId, entrada.texto)
