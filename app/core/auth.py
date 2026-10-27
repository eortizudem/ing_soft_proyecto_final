"""Sesion por cookie y decoradores de acceso."""
from functools import wraps

from flask import g, session

from .errors import ApiError


def start_session(id_usuario):
    session.clear()
    session["uid"] = id_usuario
    session.permanent = True
    g.pop("user", None)


def start_visitor_session():
    session.clear()
    session["visitante"] = True
    session.permanent = True
    g.pop("user", None)


def end_session():
    session.clear()
    g.pop("user", None)


def current_user():
    if "user" not in g:
        from app.modules.auth import service  # import tardio: evita ciclos

        g.user = service.user_from_session(session)
    return g.user


def has_permission(user, permiso):
    return bool(user) and permiso in user["permisos"]


def require_login():
    """Devuelve el usuario actual o lanza 401."""
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
    @wraps(fn)
    def wrapper(*a, **kw):
        require_login()
        return fn(*a, **kw)

    return wrapper


def permission_required(permiso):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            require_permission(permiso)
            return fn(*a, **kw)

        return wrapper

    return deco
