"""Capa CONTROLLER (HTTP) de errores: endpoint publico `/api/errores`. Delega en `service.py`."""
from flask import request

from app.core.http import body, ok

from . import bp, service


@bp.post("/api/errores")
def reportar():
    """POST /api/errores. Errores de JavaScript reportados por el navegador (hook global de main.js).

    Permiso: ninguno (publico, tambien sin sesion), con limite de frecuencia por IP y global.
    Payload JSON: `{mensaje, ruta?, origen?}` (un cuerpo no JSON se trata como vacio).
    Respuesta 200: `{ok: true, registrado: bool}`; nunca devuelve error para no provocar mas peticiones del navegador.
    """
    return ok(**service.reportar(body(), request.remote_addr or "?"))
