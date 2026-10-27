from app.core.auth import current_user, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/compras")
@permission_required("compras")
def listar():
    return service.listar()


@bp.get("/api/compras/presupuesto")
@permission_required("compras")
def presupuesto():
    return service.presupuesto(query_args({"mes": ""})["mes"])


@bp.get("/api/compras/<int:id_solicitud>")
@permission_required("compras")
def obtener(id_solicitud):
    return service.obtener(id_solicitud)


@bp.post("/api/compras")
@permission_required("compras")
def crear():
    return created(service.crear(body(), current_user()))


@bp.post("/api/compras/<int:id_solicitud>/enviar")
@permission_required("compras")
def enviar(id_solicitud):
    return service.enviar(id_solicitud, current_user())


@bp.post("/api/compras/<int:id_solicitud>/cancelar")
@permission_required("compras")
def cancelar(id_solicitud):
    return service.cancelar(id_solicitud, current_user())


@bp.post("/api/compras/<int:id_solicitud>/recibir")
@permission_required("compras")
def recibir(id_solicitud):
    return service.recibir(id_solicitud, body(), current_user())
