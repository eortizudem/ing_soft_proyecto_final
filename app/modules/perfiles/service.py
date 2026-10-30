"""Servicio de `perfiles` (capa service MVC): consulta y edición de la matriz de permisos por perfil (RF-02)."""

from app.core.bitacora import audit
from app.core.errors import ApiError
from app.core.validators import Bool, validate

from . import model

SCHEMA = {"habilitado": Bool(msg="El campo habilitado debe ser verdadero o falso.")}


def obtener():
    """Devuelve roles, permisos y la matriz de permisos.

    Returns:
        Dict con `roles`, `permisos` y `matriz` ({rol: {permiso: bool}}).
    """
    matriz = {r["nombre"]: {} for r in model.roles()}
    for row in model.matriz_rows():
        matriz[row["rol"]][row["permiso"]] = row["habilitado"]
    return {"roles": model.roles(), "permisos": model.permisos(), "matriz": matriz}


@audit("permiso_cambio", lambda r, a: f"{a['rol']}/{a['permiso']} = "
       f"{'habilitado' if a['data']['habilitado'] else 'deshabilitado'}")
def cambiar(rol, permiso, data, actor):
    """Habilita o deshabilita un permiso de un perfil (RF-02). Auditada como `permiso_cambio`.

    El admin no puede perder los permisos `usuarios` ni `perfiles`.

    Args:
        rol: Nombre del perfil.
        permiso: Nombre del permiso.
        data: Payload con `habilitado` (bool).
        actor: Usuario autenticado.

    Returns:
        La matriz actualizada (ver `obtener`).

    Raises:
        ApiError: 400 si `habilitado` no es booleano o se quita un permiso protegido del admin;
            404 si el perfil o el permiso no existen.
    """
    habilitado = validate(data, SCHEMA)["habilitado"]
    rol_ok, permiso_ok = model.exists(rol, permiso)
    if not rol_ok:
        raise ApiError("No se encontró el perfil.", 404)
    if not permiso_ok:
        raise ApiError("No se encontró el permiso.", 404)
    if rol == "admin" and permiso in ("usuarios", "perfiles") and not habilitado:
        raise ApiError("El administrador no puede perder los permisos de usuarios ni perfiles.")
    model.set_habilitado(rol, permiso, habilitado)
    return obtener()
