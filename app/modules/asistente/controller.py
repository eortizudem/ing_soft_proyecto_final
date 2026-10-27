from app.core.auth import current_user, permission_required
from app.core.http import body, query_args

from . import bp, service


@bp.post("/api/asistente/mensajes")
@permission_required("asistente")
def mensaje():
    return service.enviar_mensaje(body(), current_user())


@bp.get("/api/asistente/conversaciones/<int:id_conversacion>")
@permission_required("asistente")
def conversacion(id_conversacion):
    return service.obtener(id_conversacion, current_user())


@bp.post("/api/asistente/conversaciones/<int:id_conversacion>/opinion")
@permission_required("asistente")
def valorar(id_conversacion):
    return service.valorar(id_conversacion, body(), current_user())


@bp.get("/api/asistente/consultas")
@permission_required("prestamos")
def consultas_bibliotecario():
    return service.consultas_bibliotecario(current_user(), **query_args({"estado": ""}))


@bp.post("/api/asistente/consultas/<int:id_conversacion>/resolver")
@permission_required("prestamos")
def resolver(id_conversacion):
    return service.resolver(id_conversacion, body(), current_user())
