"""Controlador de `perfiles` (capa controller MVC): endpoints HTTP bajo `/api/roles` (RF-02)."""

from app.core.auth import current_user, login_required, permission_required
from app.core.http import body

from . import bp, service


@bp.get("/api/roles")
@login_required
def obtener():
    """GET /api/roles — matriz de perfiles y permisos. Requiere sesión. Respuesta: roles, permisos y matriz."""
    return service.obtener()


@bp.put("/api/roles/<rol>/permisos/<permiso>")
@permission_required("perfiles")
def cambiar(rol, permiso):
    """PUT /api/roles/<rol>/permisos/<permiso> — cambia un permiso. Permiso requerido: `perfiles`.
    Payload: {habilitado: bool}. Respuesta: matriz actualizada. Errores: 400 (valor inválido, permiso protegido del admin), 404.
    """
    return service.cambiar(rol, permiso, body(), current_user())
