from app.core.bitacora import audit
from app.core.errors import ApiError
from app.core.validators import Bool, validate

from . import model

SCHEMA = {"habilitado": Bool(msg="El campo habilitado debe ser verdadero o falso.")}


def obtener():
    matriz = {r["nombre"]: {} for r in model.roles()}
    for row in model.matriz_rows():
        matriz[row["rol"]][row["permiso"]] = row["habilitado"]
    return {"roles": model.roles(), "permisos": model.permisos(), "matriz": matriz}


@audit("permiso_cambio", lambda r, a: f"{a['rol']}/{a['permiso']} = "
       f"{'habilitado' if a['data']['habilitado'] else 'deshabilitado'}")
def cambiar(rol, permiso, data, actor):
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
