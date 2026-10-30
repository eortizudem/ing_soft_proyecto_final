"""Sesion por cookie y decoradores de acceso."""
from functools import wraps

from flask import g, session

from .errors import ApiError


def start_session(id_usuario):
    """Inicia sesion autenticada: limpia la sesion previa, guarda `uid` y la hace permanente."""
    session.clear()
    session["uid"] = id_usuario
    session.permanent = True
    g.pop("user", None)


def start_visitor_session():
    """Inicia sesion de visitante (sin usuario en BD): limpia la previa y marca `visitante`."""
    session.clear()
    session["visitante"] = True
    session.permanent = True
    g.pop("user", None)


def end_session():
    """Cierra la sesion y descarta el usuario cacheado en `g`."""
    session.clear()
    g.pop("user", None)


def current_user():
    """Usuario de la sesion (dict con `permisos`) o None; se resuelve una vez por peticion y se cachea en `g`."""
    if "user" not in g:
        from app.modules.auth import service  # import tardio: evita ciclos

        g.user = service.user_from_session(session)
    return g.user


def has_permission(user, permiso):
    """True si hay usuario y su lista de permisos incluye `permiso`."""
    return bool(user) and permiso in user["permisos"]


def require_login():
    """Devuelve el usuario actual o lanza ApiError 401."""
    user = current_user()
    if not user:
        raise ApiError("Debes iniciar sesión.", 401)
    return user


def require_permission(permiso, user=None):
    """Lanza 401 sin sesion o 403 sin `permiso`; devuelve el usuario."""
    user = user or require_login()
    if permiso not in user["permisos"]:
        raise ApiError("No tienes permiso para realizar esta acción.", 403)
    return user


def login_required(fn):
    """Decorador: exige sesion (401 via `require_login`) antes de ejecutar la vista `fn`."""
    @wraps(fn)
    def wrapper(*a, **kw):
        """Exige sesion y delega en la vista."""
        require_login()
        return fn(*a, **kw)

    return wrapper


def permission_required(permiso):
    """Decorador de fabrica: exige sesion (401) y `permiso` (403) antes de ejecutar la vista.

    Args:
        permiso: nombre del permiso requerido.
    """
    def deco(fn):
        """Envuelve la vista `fn` con la verificacion de permiso."""
        @wraps(fn)
        def wrapper(*a, **kw):
            """Exige el permiso y delega en la vista."""
            require_permission(permiso)
            return fn(*a, **kw)

        return wrapper

    return deco
