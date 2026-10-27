from app.core import parametros
from app.core.auth import current_user, has_permission

from . import model

PERSONAL = ("usuarios", "catalogo", "reportes", "prestamos", "compras")


def stats(actor=None):
    """Personal (cualquier permiso de gestión): conteos globales + presupuesto. Todos: `mio` (estado propio)."""
    actor = actor or current_user()
    out = {"mio": model.mio(actor["id_usuario"])}
    if any(has_permission(actor, p) for p in PERSONAL):
        out.update(model.stats())
        out["presupuesto_mensual_usd"] = parametros.presupuesto_mensual()
        out["presupuesto_usado_usd"] = model.usado_mes()
    return out
