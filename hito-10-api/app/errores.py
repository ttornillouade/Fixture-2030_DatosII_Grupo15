"""Errores de la API. Cada uno se traduce a un código HTTP y a un JSON {code, message, requestId}."""


class ErrorApi(Exception):
    status = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, code: str | None = None, causa: str | None = None):
        super().__init__(message)
        self.message = message
        # Causa técnica (tipo de excepción del driver): va al log de la request, nunca a la respuesta.
        self.causa = causa
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
    """La base rechazó la conexión o falló (caída, credenciales, contexto). No se exponen detalles internos."""

    status = 503
    code = "DEPENDENCY_UNAVAILABLE"

    def __init__(self, fuente: str, causa: str | None = None):
        super().__init__(f"La fuente {fuente} no está disponible en este momento", causa=causa)
        self.fuente = fuente


class DependenciaTimeout(ErrorApi):
    """La base no respondió dentro de TIMEOUT_S. En una escritura, el resultado es desconocido."""

    status = 504
    code = "DEPENDENCY_TIMEOUT"

    def __init__(self, fuente: str, causa: str | None = None):
        super().__init__(f"La fuente {fuente} no respondió a tiempo", causa=causa)
        self.fuente = fuente
