from app.core import repo


def roles():
    return repo.fetch_all("SELECT nombre, descripcion FROM rol ORDER BY id_rol")


def permisos():
    return repo.fetch_all("SELECT nombre, descripcion FROM permiso ORDER BY id_permiso")


def matriz_rows():
    return repo.fetch_all(
        """SELECT r.nombre AS rol, p.nombre AS permiso, rp.habilitado
           FROM rol_permiso rp JOIN rol r ON r.id_rol = rp.id_rol JOIN permiso p ON p.id_permiso = rp.id_permiso"""
    )


def exists(rol, permiso):
    r = repo.fetch_one("SELECT (SELECT count(*) FROM rol WHERE nombre=%s) AS r, "
                    "(SELECT count(*) FROM permiso WHERE nombre=%s) AS p", (rol, permiso))
    return r["r"] > 0, r["p"] > 0


def set_habilitado(rol, permiso, habilitado):
    repo.execute(
        """UPDATE rol_permiso SET habilitado = %s
           WHERE id_rol = (SELECT id_rol FROM rol WHERE nombre = %s)
             AND id_permiso = (SELECT id_permiso FROM permiso WHERE nombre = %s)""",
        (habilitado, rol, permiso),
    )
