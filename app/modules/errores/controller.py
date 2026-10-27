from flask import request

from app.core.http import body, ok

from . import bp, service


@bp.post("/api/errores")
def reportar():
    """Errores de JavaScript reportados por el navegador (hook global de main.js). Publico y con limite de frecuencia."""
    return ok(**service.reportar(body(), request.remote_addr or "?"))
