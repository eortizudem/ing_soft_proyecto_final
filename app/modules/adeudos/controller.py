from decimal import Decimal, InvalidOperation

from app.core.auth import current_user, permission_required
from app.core.errors import ApiError
from app.core.http import body, created, query_args

from . import bp, service


def _tc(raw):
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise ApiError("El tipo de cambio debe ser un número mayor que 0.")


@bp.get("/api/adeudos")
@permission_required("adeudos")
def listar():
    return service.listar(**query_args({"estado": "", "tipo": "", "q": "", "matricula": "", "limite": 0}))


@bp.get("/api/adeudos/reposicion")
@permission_required("adeudos")
def reposicion():
    a = query_args({"id_libro": 0, "tipo_cambio": (None, _tc)})
    return service.reposicion(a["id_libro"], a["tipo_cambio"])


@bp.get("/api/adeudos/prestamo/<int:id_prestamo>")
@permission_required("adeudos")
def previsualizar(id_prestamo):
    return service.previsualizar(id_prestamo, query_args({"tipo_cambio": "", "porcentaje": ""}))


@bp.get("/api/adeudos/<int:id_adeudo>")
@permission_required("adeudos")
def obtener(id_adeudo):
    return service.obtener(id_adeudo)


@bp.post("/api/adeudos/<int:id_adeudo>/pago")
@permission_required("adeudos")
def pagar(id_adeudo):
    return service.pagar(id_adeudo, body(), current_user())


@bp.post("/api/adeudos/<int:id_adeudo>/cancelar")
@permission_required("adeudos")
def cancelar(id_adeudo):
    return service.cancelar(id_adeudo, body(), current_user())


@bp.post("/api/adeudos/perdida")
@permission_required("adeudos")
def perdida():
    return created(service.perdida(body(), current_user()))


@bp.post("/api/adeudos/danio")
@permission_required("adeudos")
def danio():
    return created(service.danio(body(), current_user()))


@bp.get("/api/tipo-cambio")
@permission_required("adeudos")
def tipo_cambio():
    return service.tipo_cambio()
