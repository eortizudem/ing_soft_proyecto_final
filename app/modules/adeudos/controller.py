"""Controlador de adeudos: endpoints HTTP bajo `/api/adeudos` y `/api/tipo-cambio` (capa controller del MVC).

Todas las rutas exigen el permiso `adeudos` y delegan en `service`.
"""
from decimal import Decimal, InvalidOperation

from app.core.auth import current_user, permission_required
from app.core.errors import ApiError
from app.core.http import body, created, query_args

from . import bp, service


def _tc(raw):
    """Convierte el parámetro de query `tipo_cambio` a Decimal.

    Args:
        raw: Texto recibido en la query.

    Returns:
        Decimal: Tipo de cambio.

    Raises:
        ApiError: 400 si no es un número.
    """
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise ApiError("El tipo de cambio debe ser un número mayor que 0.")


@bp.get("/api/adeudos")
@permission_required("adeudos")
def listar():
    """GET /api/adeudos — lista adeudos (permiso `adeudos`).

    Query: `estado`, `tipo`, `q`, `matricula`, `limite`.

    Returns:
        JSON: lista de adeudos.
    """
    return service.listar(**query_args({"estado": "", "tipo": "", "q": "", "matricula": "", "limite": 0}))


@bp.get("/api/adeudos/reposicion")
@permission_required("adeudos")
def reposicion():
    """GET /api/adeudos/reposicion — valor de reposición de un libro (permiso `adeudos`, RN-04).

    Query: `id_libro`, `tipo_cambio` opcional.

    Returns:
        JSON: `valor_usd`, `tipo_cambio`, `monto_mxn`, `fuente`. Errores: 400.
    """
    a = query_args({"id_libro": 0, "tipo_cambio": (None, _tc)})
    return service.reposicion(a["id_libro"], a["tipo_cambio"])


@bp.get("/api/adeudos/prestamo/<int:id_prestamo>")
@permission_required("adeudos")
def previsualizar(id_prestamo):
    """GET /api/adeudos/prestamo/<id_prestamo> — previsualiza montos de pérdida/daño (permiso `adeudos`).

    Query: `tipo_cambio`, `porcentaje` opcionales.

    Returns:
        JSON: datos del préstamo y montos calculados. Errores: 400, 404.
    """
    return service.previsualizar(id_prestamo, query_args({"tipo_cambio": "", "porcentaje": ""}))


@bp.get("/api/adeudos/<int:id_adeudo>")
@permission_required("adeudos")
def obtener(id_adeudo):
    """GET /api/adeudos/<id_adeudo> — detalle de un adeudo (permiso `adeudos`).

    Returns:
        JSON: adeudo con referencia y motivo de cancelación. Errores: 404.
    """
    return service.obtener(id_adeudo)


@bp.post("/api/adeudos/<int:id_adeudo>/pago")
@permission_required("adeudos")
def pagar(id_adeudo):
    """POST /api/adeudos/<id_adeudo>/pago — registra el pago (permiso `adeudos`, D-10).

    Body: `referencia_tesoreria`, `fecha_pago` opcional.

    Returns:
        JSON: adeudo pagado. Errores: 400, 404, 409 si no está pendiente.
    """
    return service.pagar(id_adeudo, body(), current_user())


@bp.post("/api/adeudos/<int:id_adeudo>/cancelar")
@permission_required("adeudos")
def cancelar(id_adeudo):
    """POST /api/adeudos/<id_adeudo>/cancelar — cancela un adeudo (permiso `adeudos`; solo rol admin).

    Body: `motivo`.

    Returns:
        JSON: adeudo cancelado. Errores: 400, 403 no admin, 404, 409.
    """
    return service.cancelar(id_adeudo, body(), current_user())


@bp.post("/api/adeudos/perdida")
@permission_required("adeudos")
def perdida():
    """POST /api/adeudos/perdida — registra una pérdida (permiso `adeudos`, RN-04).

    Body: `id_prestamo`, `tipo_cambio` y `observacion` opcionales.

    Returns:
        JSON 201: adeudos generados y monto de reposición. Errores: 400, 404, 409.
    """
    return created(service.perdida(body(), current_user()))


@bp.post("/api/adeudos/danio")
@permission_required("adeudos")
def danio():
    """POST /api/adeudos/danio — registra un daño (permiso `adeudos`, D-08).

    Body: `id_prestamo`, `porcentaje`, `observacion`, `dar_baja` opcionales.

    Returns:
        JSON 201: adeudo, devolución y espera notificada. Errores: 400, 404, 409.
    """
    return created(service.danio(body(), current_user()))


@bp.get("/api/tipo-cambio")
@permission_required("adeudos")
def tipo_cambio():
    """GET /api/tipo-cambio — tipo de cambio USD/MXN simulado (permiso `adeudos`).

    Returns:
        JSON: `usd_mxn`, `fuente`, `nota`.
    """
    return service.tipo_cambio()
