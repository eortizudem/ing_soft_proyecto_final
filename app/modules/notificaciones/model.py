"""Capa MODEL de notificaciones (acceso a datos SQL): lee los avisos simulados guardados en `bitacora` (accion `notif_<canal>`, D-11)."""
from psycopg import sql

from app.core import repo
from app.core.notificaciones import CANALES, PREFIJO

_BASE = """
SELECT b.id_bitacora, b.accion, b.detalle, b.fecha, u.matricula, u.nombre_completo
FROM bitacora b JOIN usuario u ON u.id_usuario = b.id_usuario
"""


def list_(canal="", q="", desde=None, id_usuario=None, limite=100):
    """Notificaciones simuladas (bitacora 'notif_<canal>'), mas recientes primero (D-11).

    Args:
        canal (str): un canal de `CANALES`; vacio = todos.
        q (str): busqueda sin acentos en detalle, matricula y nombre del usuario.
        desde (date | None): fecha minima (inclusive).
        id_usuario (int | None): limita a los avisos de ese usuario ("mis notificaciones").
        limite (int): maximo de filas.

    Returns:
        list[dict]: `id_bitacora`, `accion`, `detalle`, `fecha`, `matricula`, `nombre_completo`.
    """
    acciones = [PREFIJO + canal] if canal else [PREFIJO + c for c in CANALES]
    where, params = repo.build_where(
        {"b.accion": acciones, "b.fecha__gte": desde, "b.id_usuario": id_usuario},
        search=(q, ["b.detalle", "u.matricula", "u.nombre_completo"]))
    query = sql.SQL(_BASE + " WHERE ") + where + sql.SQL(" ORDER BY b.fecha DESC, b.id_bitacora DESC LIMIT %s")
    return repo.fetch_all(query, params + [limite])
