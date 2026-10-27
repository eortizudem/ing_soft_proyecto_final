"""Bitacora de acciones: log() directo o decorador @audit en funciones de servicio."""
import inspect
from functools import wraps

from . import db


def log(id_usuario, accion, detalle=""):
    """Registra en bitacora. Sin usuario en BD (visitante) no se registra."""
    if id_usuario is None:
        return
    db.execute(
        "INSERT INTO bitacora(id_usuario, accion, detalle) VALUES (%s,%s,%s)",
        (id_usuario, accion[:40], str(detalle)[:200]),
    )


def _call(fn, result, args):
    return fn(result, args) if len(inspect.signature(fn).parameters) > 1 else fn(result)


def audit(accion, detail=None, actor_arg="actor"):
    """Tras ejecutarse sin error, registra en bitacora a nombre del argumento `actor_arg`.

    accion: str o fn(resultado). detail: fn(resultado) o fn(resultado, args) -> texto; args = dict de
    argumentos de la funcion decorada.

        @audit("libro_crear", lambda r: f"Alta de {r['clave']}")
        def crear(d, actor): ...
    """

    def deco(fn):
        sig = inspect.signature(fn)

        @wraps(fn)
        def wrapper(*a, **kw):
            result = fn(*a, **kw)
            args = sig.bind(*a, **kw).arguments
            actor = args.get(actor_arg)
            if actor:
                name = _call(accion, result, args) if callable(accion) else accion
                log(actor["id_usuario"], name, _call(detail, result, args) if detail else "")
            return result

        return wrapper

    return deco
