from app.core.auth import current_user, login_required, permission_required
from app.core.http import query_args

from . import bp, service

_ARGS = {"canal": "", "q": "", "desde": "", "limite": 100}


@bp.get("/api/notificaciones")
@permission_required("notificaciones")
def listar():
    return service.listar(**query_args(_ARGS))


@bp.get("/api/notificaciones/mias")
@login_required
def mias():
    return service.mias(current_user()["id_usuario"], **query_args(_ARGS))
