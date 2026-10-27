from psycopg import sql

from app.core import repo
from app.core.notificaciones import CANALES, PREFIJO

_BASE = """
SELECT b.id_bitacora, b.accion, b.detalle, b.fecha, u.matricula, u.nombre_completo
FROM bitacora b JOIN usuario u ON u.id_usuario = b.id_usuario
"""


def list_(canal="", q="", desde=None, id_usuario=None, limite=100):
    """Notificaciones simuladas (bitacora 'notif_<canal>'), mas recientes primero."""
    acciones = [PREFIJO + canal] if canal else [PREFIJO + c for c in CANALES]
    where, params = repo.build_where(
        {"b.accion": acciones, "b.fecha__gte": desde, "b.id_usuario": id_usuario},
        search=(q, ["b.detalle", "u.matricula", "u.nombre_completo"]))
    query = sql.SQL(_BASE + " WHERE ") + where + sql.SQL(" ORDER BY b.fecha DESC, b.id_bitacora DESC LIMIT %s")
    return repo.fetch_all(query, params + [limite])
