from app.core.auth import current_user, login_required, permission_required
from app.core.http import body

from . import bp, service


@bp.get("/api/roles")
@login_required
def obtener():
    return service.obtener()


@bp.put("/api/roles/<rol>/permisos/<permiso>")
@permission_required("perfiles")
def cambiar(rol, permiso):
    return service.cambiar(rol, permiso, body(), current_user())
