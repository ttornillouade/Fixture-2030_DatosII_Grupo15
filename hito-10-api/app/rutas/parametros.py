"""Parámetros y respuestas de error compartidos por las rutas."""
from typing import Annotated

from fastapi import Path, Request

from app.esquemas import Error

PartidoCodigo = Annotated[str, Path(pattern=r"^P[0-9]{3}$", description="Código de partido", examples=["P001"])]


def errores(*codigos: int) -> dict:
    descripciones = {400: "La request no cumple el contrato", 404: "Recurso inexistente",
                     409: "La operación no está permitida por el estado actual",
                     503: "La fuente de datos no está disponible"}
    return {c: {"model": Error, "description": descripciones[c]} for c in codigos}


def fuente(nombre: str):
    """Dependencia de ruta: deja en la request qué base atiende el endpoint, para el log."""
    def registrar(request: Request):
        request.state.fuente = nombre
    return registrar
