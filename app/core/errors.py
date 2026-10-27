from flask import jsonify, request, session
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Error de negocio -> `{"error": message, **extra}` con el status HTTP indicado."""

    def __init__(self, message, status=400, extra=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra or {}

    @classmethod
    def reglas(cls, motivos, message="No se cumplen las condiciones."):
        """422 con `motivos: [{codigo, mensaje}]` (reglas de negocio incumplidas)."""
        return cls(message, 422, {"motivos": list(motivos)})


def motivo(codigo, mensaje):
    return {"codigo": codigo, "mensaje": mensaje}


def exigir(motivos, message="No se cumplen las condiciones."):
    """Lanza ApiError.reglas si hay motivos; no hace nada si la lista esta vacia."""
    if motivos:
        raise ApiError.reglas(motivos, message)


def register(app):
    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify(error=e.message, **e.extra), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):
        if request.path.startswith("/api"):
            msgs = {404: "Recurso no encontrado.", 405: "Método no permitido."}
            return jsonify(error=msgs.get(e.code, e.description)), e.code
        return e

    @app.errorhandler(Exception)
    def unexpected(e):
        app.logger.exception("Error inesperado")
        # PS-S3-06: el 500 queda en la bitacora de errores (usuario de la sesion si lo hay).
        from . import errores

        errores.registrar("servidor", f"{request.method} {request.path}: {type(e).__name__}: {e}", session.get("uid"))
        return jsonify(error="Error interno del servidor."), 500
