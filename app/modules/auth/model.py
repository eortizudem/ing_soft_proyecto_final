from datetime import datetime, timedelta

from app.core import repo

_USER_SQL = """
SELECT u.id_usuario, u.matricula, u.nombre_completo, u.correo, u.contrasena_hash, u.estado,
       r.nombre AS rol, r.descripcion AS rol_descripcion
FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
"""


def find_by_matricula(matricula):
    return repo.fetch_one(_USER_SQL + " WHERE u.matricula = %s", (matricula,))


def find_by_id(id_usuario):
    return repo.fetch_one(_USER_SQL + " WHERE u.id_usuario = %s", (id_usuario,))


def find_by_correo(correo):
    return repo.fetch_one(_USER_SQL + " WHERE lower(u.correo) = lower(%s)", (correo,))


def get_rol(nombre):
    return repo.fetch_one("SELECT nombre, descripcion FROM rol WHERE nombre = %s", (nombre,))


def permisos_habilitados(rol):
    rows = repo.fetch_all(
        """SELECT p.nombre FROM rol_permiso rp
           JOIN rol r ON r.id_rol = rp.id_rol JOIN permiso p ON p.id_permiso = rp.id_permiso
           WHERE r.nombre = %s AND rp.habilitado ORDER BY p.id_permiso""",
        (rol,),
    )
    return [r["nombre"] for r in rows]


def create_token(id_usuario, token, minutos=30):
    now = datetime.now()
    repo.insert("recuperacion_contrasena", {"id_usuario": id_usuario, "token": token, "fecha_envio": now,
                                            "fecha_expira": now + timedelta(minutes=minutos)}, returning=None)


def find_valid_token(token):
    return repo.fetch_one(
        "SELECT * FROM recuperacion_contrasena WHERE token = %s AND NOT usado AND fecha_expira > now()::timestamp",
        (token,),
    )


def mark_token_used(id_token):
    repo.update("recuperacion_contrasena", "id_token", id_token, {"usado": True}, returning=None)


def set_password(id_usuario, hash_):
    repo.update("usuario", "id_usuario", id_usuario, {"contrasena_hash": hash_}, returning=None)
