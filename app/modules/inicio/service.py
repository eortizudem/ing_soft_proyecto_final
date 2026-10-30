"""Servicio de `inicio` (capa service MVC): decide qué estadísticas del tablero ve cada usuario según sus permisos."""

from app.core import parametros
from app.core.auth import current_user, has_permission

from . import model

PERSONAL = ("usuarios", "catalogo", "reportes", "prestamos", "compras")


def stats(actor=None):
    """Estadísticas del tablero.

    Personal (cualquier permiso de gestión en `PERSONAL`): conteos globales y presupuesto mensual (D-22).
    Todos: `mio` (estado propio).

    Args:
        actor: Usuario; si es None se toma el usuario de la sesión.

    Returns:
        Dict con `mio` y, solo para personal, los conteos globales, `presupuesto_mensual_usd` y `presupuesto_usado_usd`.
    """
    actor = actor or current_user()
    out = {"mio": model.mio(actor["id_usuario"])}
    if any(has_permission(actor, p) for p in PERSONAL):
        out.update(model.stats())
        out["presupuesto_mensual_usd"] = parametros.presupuesto_mensual()
        out["presupuesto_usado_usd"] = model.usado_mes()
    return out
