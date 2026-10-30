"""Excepcion de negocio `ApiError`, helpers de motivos (422) y manejadores de error de Flask (capa transversal)."""
from flask import jsonify, request, session
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Error de negocio -> `{"error": message, **extra}` con el status HTTP indicado."""

    def __init__(self, message, status=400, extra=None):
        """Crea el error de negocio.

        Args:
            message: texto en espanol para el usuario.
            status: codigo HTTP (400 por defecto).
            extra: dict que se mezcla en el cuerpo JSON de la respuesta.
        """
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra or {}

    @classmethod
    def reglas(cls, motivos, message="No se cumplen las condiciones."):
        """422 con `motivos: [{codigo, mensaje}]` (reglas de negocio incumplidas).

        Args:
            motivos: iterable de dicts creados con `motivo()`.
            message: mensaje general del error.

        Returns:
            ApiError con status 422 (la excepcion se devuelve, no se lanza).
        """
        return cls(message, 422, {"motivos": list(motivos)})


def motivo(codigo, mensaje):
    """Motivo de incumplimiento `{codigo, mensaje}`; `codigo` es estable para el frontend y las pruebas."""
    return {"codigo": codigo, "mensaje": mensaje}


def exigir(motivos, message="No se cumplen las condiciones."):
    """Lanza ApiError.reglas si hay motivos; no hace nada si la lista esta vacia."""
    if motivos:
        raise ApiError.reglas(motivos, message)


def register(app):
    """Registra los manejadores de error: `ApiError`, `HTTPException` (JSON solo bajo /api) y cualquier excepcion (500)."""
    @app.errorhandler(ApiError)
    def api_error(e):
        """Responde `{"error", **extra}` con el status del `ApiError`."""
        return jsonify(error=e.message, **e.extra), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):
        """Errores HTTP de Werkzeug: JSON bajo /api (mensajes en espanol para 404/405); fuera de /api, la pagina por defecto."""
        if request.path.startswith("/api"):
            msgs = {404: "Recurso no encontrado.", 405: "Método no permitido."}
            return jsonify(error=msgs.get(e.code, e.description)), e.code
        return e

    @app.errorhandler(Exception)
    def unexpected(e):
        """Excepcion no controlada: la registra en log y en la bitacora de errores (PS-S3-06) y responde 500 generico."""
        app.logger.exception("Error inesperado")
        # PS-S3-06: el 500 queda en la bitacora de errores (usuario de la sesion si lo hay).
        from . import errores

        errores.registrar("servidor", f"{request.method} {request.path}: {type(e).__name__}: {e}", session.get("uid"))
        return jsonify(error="Error interno del servidor."), 500
