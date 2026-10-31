from fastapi import APIRouter, Depends, Request

from app import servicios
from app.esquemas import Salud, SaludDependencias
from app.rutas.parametros import fuente

router = APIRouter(tags=["Salud"])


@router.get("/salud", response_model=Salud, summary="Liveness: el proceso de la API responde")
def salud():
    """No consulta ninguna base: solo indica que el proceso está vivo y atiende requests."""
    return {"estado": "up"}


@router.get("/salud/dependencias", response_model=SaludDependencias, dependencies=[Depends(fuente("Salud"))],
            summary="Diagnóstico por dependencia (un ping a cada base)")
def salud_dependencias(request: Request):
    """Responde 200 aunque haya bases caídas: es un informe, y el estado de cada base va en el cuerpo
    (up, down, unknown, not_configured). Hace 6 pings en paralelo y tarda a lo sumo TIMEOUT_S: no se
    usa en las requests normales."""
    resultado = servicios.salud_dependencias()
    # La causa de cada base que falló va a la línea de log de esta request, no a la respuesta.
    request.state.causa = "; ".join(f"{d['nombre']}: {d['causa']}" for d in resultado["dependencias"] if d["causa"])
    return resultado
