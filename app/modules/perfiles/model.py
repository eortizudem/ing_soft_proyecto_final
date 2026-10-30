"""Modelo de `perfiles` (capa model MVC): acceso a datos SQL de roles, permisos y la matriz `rol_permiso` (RF-02)."""

from app.core import repo


def roles():
    """Lista los perfiles (roles) en orden de definición.

    Returns:
        Lista de dicts (nombre, descripcion).
    """
    return repo.fetch_all("SELECT nombre, descripcion FROM rol ORDER BY id_rol")


def permisos():
    """Lista los permisos del sistema en orden de definición.

    Returns:
        Lista de dicts (nombre, descripcion).
    """
    return repo.fetch_all("SELECT nombre, descripcion FROM permiso ORDER BY id_permiso")


def matriz_rows():
    """Filas planas de la matriz rol-permiso.

    Returns:
        Lista de dicts (rol, permiso, habilitado).
    """
    return repo.fetch_all(
        """SELECT r.nombre AS rol, p.nombre AS permiso, rp.habilitado
           FROM rol_permiso rp JOIN rol r ON r.id_rol = rp.id_rol JOIN permiso p ON p.id_permiso = rp.id_permiso"""
    )


def exists(rol, permiso):
    """Verifica si existen un rol y un permiso por nombre.

    Args:
        rol: Nombre del rol.
        permiso: Nombre del permiso.

    Returns:
        Tupla (rol_existe, permiso_existe).
    """
    r = repo.fetch_one("SELECT (SELECT count(*) FROM rol WHERE nombre=%s) AS r, "
                    "(SELECT count(*) FROM permiso WHERE nombre=%s) AS p", (rol, permiso))
    return r["r"] > 0, r["p"] > 0


def set_habilitado(rol, permiso, habilitado):
    """Habilita o deshabilita un permiso para un rol.

    Args:
        rol: Nombre del rol.
        permiso: Nombre del permiso.
        habilitado: Nuevo valor.
    """
    repo.execute(
        """UPDATE rol_permiso SET habilitado = %s
           WHERE id_rol = (SELECT id_rol FROM rol WHERE nombre = %s)
             AND id_permiso = (SELECT id_permiso FROM permiso WHERE nombre = %s)""",
        (habilitado, rol, permiso),
    )
