"""Capa MODEL de auth (acceso a datos SQL): usuarios con su rol, permisos habilitados y tokens de recuperacion de contrasena."""
from datetime import datetime, timedelta

from app.core import repo

# Consulta base de usuario + rol; los `find_*` le agregan el WHERE.
_USER_SQL = """
SELECT u.id_usuario, u.matricula, u.nombre_completo, u.correo, u.contrasena_hash, u.estado,
       r.nombre AS rol, r.descripcion AS rol_descripcion
FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
"""


def find_by_matricula(matricula):
    """Busca un usuario por matricula.

    Args:
        matricula (str): matricula (la comparacion es exacta; el service la envia en mayusculas).

    Returns:
        dict | None: usuario con `rol` y `rol_descripcion`, o `None`.
    """
    return repo.fetch_one(_USER_SQL + " WHERE u.matricula = %s", (matricula,))


def find_by_id(id_usuario):
    """Busca un usuario por id.

    Args:
        id_usuario (int): id del usuario.

    Returns:
        dict | None: usuario con rol, o `None`.
    """
    return repo.fetch_one(_USER_SQL + " WHERE u.id_usuario = %s", (id_usuario,))


def find_by_correo(correo):
    """Busca un usuario por correo sin distinguir mayusculas.

    Args:
        correo (str): correo institucional.

    Returns:
        dict | None: usuario con rol, o `None`.
    """
    return repo.fetch_one(_USER_SQL + " WHERE lower(u.correo) = lower(%s)", (correo,))


def get_rol(nombre):
    """Obtiene un rol por nombre.

    Args:
        nombre (str): nombre del rol (p. ej. `visitante`).

    Returns:
        dict | None: `nombre`, `descripcion`, o `None`.
    """
    return repo.fetch_one("SELECT nombre, descripcion FROM rol WHERE nombre = %s", (nombre,))


def permisos_habilitados(rol):
    """Permisos habilitados del rol (RBAC).

    Args:
        rol (str): nombre del rol.

    Returns:
        list[str]: nombres de permiso con `rol_permiso.habilitado`.
    """
    rows = repo.fetch_all(
        """SELECT p.nombre FROM rol_permiso rp
           JOIN rol r ON r.id_rol = rp.id_rol JOIN permiso p ON p.id_permiso = rp.id_permiso
           WHERE r.nombre = %s AND rp.habilitado ORDER BY p.id_permiso""",
        (rol,),
    )
    return [r["nombre"] for r in rows]


def create_token(id_usuario, token, minutos=30):
    """Guarda un token de recuperacion de contrasena con vigencia limitada.

    Args:
        id_usuario (int): usuario que solicito la recuperacion.
        token (str): codigo generado.
        minutos (int): vigencia en minutos (30 por defecto).
    """
    now = datetime.now()
    repo.insert("recuperacion_contrasena", {"id_usuario": id_usuario, "token": token, "fecha_envio": now,
                                            "fecha_expira": now + timedelta(minutes=minutos)}, returning=None)


def find_valid_token(token):
    """Busca un token de recuperacion vigente (no usado y no expirado).

    Args:
        token (str): codigo de recuperacion.

    Returns:
        dict | None: fila `recuperacion_contrasena` o `None` si no es valido.
    """
    return repo.fetch_one(
        "SELECT * FROM recuperacion_contrasena WHERE token = %s AND NOT usado AND fecha_expira > now()::timestamp",
        (token,),
    )


def mark_token_used(id_token):
    """Marca un token como usado (de un solo uso).

    Args:
        id_token (int): id del token.
    """
    repo.update("recuperacion_contrasena", "id_token", id_token, {"usado": True}, returning=None)


def set_password(id_usuario, hash_):
    """Actualiza el hash de contrasena del usuario.

    Args:
        id_usuario (int): usuario a actualizar.
        hash_ (str): hash generado con werkzeug.
    """
    repo.update("usuario", "id_usuario", id_usuario, {"contrasena_hash": hash_}, returning=None)
