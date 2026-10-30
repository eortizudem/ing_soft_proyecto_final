"""Capa CONTROLLER (HTTP) del asistente: endpoints `/api/asistente/*`. Delega toda la logica en `service.py`."""
from app.core.auth import current_user, permission_required
from app.core.http import body, query_args

from . import bp, service


@bp.post("/api/asistente/mensajes")
@permission_required("asistente")
def mensaje():
    """POST /api/asistente/mensajes. Permiso: `asistente` (incluye visitantes, D-26).

    Payload JSON: `{texto, id_conversacion?, canal?}`.
    Respuesta 200: `{id_conversacion, respuesta: {texto, intencion, con_bibliotecario, libros?, enlaces?}}`.
    Errores: 400 payload invalido; 401 sin sesion; 403 sin permiso; 404 conversacion ajena o inexistente.
    """
    return service.enviar_mensaje(body(), current_user())


@bp.get("/api/asistente/conversaciones/<int:id_conversacion>")
@permission_required("asistente")
def conversacion(id_conversacion):
    """GET /api/asistente/conversaciones/<id>. Permiso: `asistente` (dueno; el bibliotecario solo si fue escalada).

    Respuesta 200: conversacion con `mensajes` (y `usuario` para personal).
    Errores: 401, 403, 404 (no existe o no es accesible).
    """
    return service.obtener(id_conversacion, current_user())


@bp.post("/api/asistente/conversaciones/<int:id_conversacion>/opinion")
@permission_required("asistente")
def valorar(id_conversacion):
    """POST /api/asistente/conversaciones/<id>/opinion. Permiso: `asistente` (solo el dueno).

    Payload JSON: `{calificacion (1-5), resuelta?}`. Respuesta 200: conversacion actualizada.
    Errores: 400 calificacion invalida; 401, 403; 404 conversacion ajena o inexistente.
    """
    return service.valorar(id_conversacion, body(), current_user())


@bp.get("/api/asistente/consultas")
@permission_required("prestamos")
def consultas_bibliotecario():
    """GET /api/asistente/consultas?estado=<"" | pendiente | resuelta>. Permiso: `prestamos` (bibliotecario).

    Respuesta 200: lista de consultas escaladas (RF-33). Errores: 400 estado invalido; 401, 403.
    """
    return service.consultas_bibliotecario(current_user(), **query_args({"estado": ""}))


@bp.post("/api/asistente/consultas/<int:id_conversacion>/resolver")
@permission_required("prestamos")
def resolver(id_conversacion):
    """POST /api/asistente/consultas/<id>/resolver. Permiso: `prestamos` (bibliotecario). Auditado (`asistente_resolver`).

    Payload JSON: `{respuesta (1-500)}`. Respuesta 200: conversacion resuelta.
    Errores: 400 respuesta invalida; 401, 403; 404 consulta inexistente o no escalada; 409 ya resuelta.
    """
    return service.resolver(id_conversacion, body(), current_user())
