"""Capa controlador de compras (HTTP): rutas `/api/compras`. Todas requieren el permiso `compras`.
"""

from app.core.auth import current_user, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/compras")
@permission_required("compras")
def listar():
    """GET /api/compras — lista de solicitudes con detalles (RF-05). Permiso: `compras`."""
    return service.listar()


@bp.get("/api/compras/presupuesto")
@permission_required("compras")
def presupuesto():
    """GET /api/compras/presupuesto — presupuesto mensual, usado y disponible (RF-05, D-22). Permiso: `compras`.

    Query: mes (AAAA-MM, opcional). Errores: 400 si el formato es inválido.
    """
    return service.presupuesto(query_args({"mes": ""})["mes"])


@bp.get("/api/compras/<int:id_solicitud>")
@permission_required("compras")
def obtener(id_solicitud):
    """GET /api/compras/<id_solicitud> — detalle de una solicitud. Permiso: `compras`. Error: 404."""
    return service.obtener(id_solicitud)


@bp.post("/api/compras")
@permission_required("compras")
def crear():
    """POST /api/compras — crea solicitud (RF-05). Permiso: `compras`.

    Payload: {justificacion, destinatario?, detalles[]}. Respuesta: 201 con la solicitud. Errores: 400 (incl. `PRESUPUESTO_EXCEDIDO`).
    """
    return created(service.crear(body(), current_user()))


@bp.post("/api/compras/<int:id_solicitud>/enviar")
@permission_required("compras")
def enviar(id_solicitud):
    """POST /api/compras/<id_solicitud>/enviar — pendiente -> enviada. Permiso: `compras`. Errores: 400, 404."""
    return service.enviar(id_solicitud, current_user())


@bp.post("/api/compras/<int:id_solicitud>/cancelar")
@permission_required("compras")
def cancelar(id_solicitud):
    """POST /api/compras/<id_solicitud>/cancelar — cancela solicitud sin recepciones. Permiso: `compras`. Errores: 404, 409."""
    return service.cancelar(id_solicitud, current_user())


@bp.post("/api/compras/<int:id_solicitud>/recibir")
@permission_required("compras")
def recibir(id_solicitud):
    """POST /api/compras/<id_solicitud>/recibir — recepción parcial/total con factura (RF-06, D-25). Permiso: `compras`.

    Payload: {factura_folio, factura_total, fecha_recepcion?, lineas[]}. Respuesta: solicitud con `pendientes_catalogar`.
    Errores: 400, 404, 409.
    """
    return service.recibir(id_solicitud, body(), current_user())
