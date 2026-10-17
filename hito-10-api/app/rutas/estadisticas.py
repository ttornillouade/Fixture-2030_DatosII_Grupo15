from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app import servicios
from app.esquemas import Estadisticas
from app.rutas.parametros import fuente, PartidoCodigo, errores

router = APIRouter(tags=["InfluxDB"], dependencies=[Depends(fuente("InfluxDB"))])


@router.get("/partidos/{codigo}/estadisticas", response_model=Estadisticas, responses=errores(400, 503),
            summary="Estadísticas por equipo en una ventana temporal")
def obtener_estadisticas(codigo: PartidoCodigo,
                         desde: Annotated[datetime, Query(examples=["2026-10-04T14:00:00Z"])],
                         hasta: Annotated[datetime, Query(examples=["2026-10-04T14:10:00Z"])],
                         agregacion: Literal["raw", "minuto"] = "raw"):
    """Ventana máxima: 15 minutos en raw (1 punto por segundo y equipo) y 3 horas por minuto.
    Una ventana sin puntos devuelve 200 con la lista vacía: InfluxDB no conoce el partido, solo observaciones."""
    return servicios.estadisticas(codigo, desde, hasta, agregacion)
