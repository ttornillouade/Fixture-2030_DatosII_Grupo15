"""Errores de la API. Cada uno se traduce a un código HTTP y a un JSON {code, message, requestId}."""


class ErrorApi(Exception):
    status = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class Validacion(ErrorApi):
    status = 400
    code = "VALIDATION_ERROR"


class NoEncontrado(ErrorApi):
    status = 404
    code = "NOT_FOUND"


class Conflicto(ErrorApi):
    status = 409
    code = "CONFLICT"


class DependenciaNoDisponible(ErrorApi):
    """La base no respondió (caída, timeout o credenciales). No se exponen detalles internos."""

    status = 503
    code = "DEPENDENCY_UNAVAILABLE"

    def __init__(self, fuente: str):
        super().__init__(f"La fuente {fuente} no está disponible en este momento")
        self.fuente = fuente
