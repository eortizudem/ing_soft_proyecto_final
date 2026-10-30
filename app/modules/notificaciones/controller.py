"""Capa CONTROLLER (HTTP) de notificaciones: endpoints `/api/notificaciones*`. Delega en `service.py`."""
from app.core.auth import current_user, login_required, permission_required
from app.core.http import query_args

from . import bp, service

# Parametros de query admitidos y su valor por defecto.
_ARGS = {"canal": "", "q": "", "desde": "", "limite": 100}


@bp.get("/api/notificaciones")
@permission_required("notificaciones")
def listar():
    """GET /api/notificaciones?canal&q&desde&limite. Permiso: `notificaciones` (personal).

    Respuesta 200: lista de avisos simulados de todos los usuarios. Errores: 400 filtro invalido; 401; 403.
    """
    return service.listar(**query_args(_ARGS))


@bp.get("/api/notificaciones/mias")
@login_required
def mias():
    """GET /api/notificaciones/mias?canal&q&desde&limite. Requiere sesion (cualquier rol; sin permiso especifico).

    Respuesta 200: avisos del usuario actual (lista vacia si es visitante). Errores: 400 filtro invalido; 401.
    """
    return service.mias(current_user()["id_usuario"], **query_args(_ARGS))
