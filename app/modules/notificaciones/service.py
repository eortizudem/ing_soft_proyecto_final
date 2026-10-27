from app.core.notificaciones import CANALES, parsear
from app.core.validators import Date, Enum, validate

from . import model

LIMITE_MAX = 500
SCHEMA = {
    "canal": Enum(CANALES, "Selecciona un canal válido.", label="canal", required=False),
    "desde": Date(label="fecha", required=False),
}


def _fila(r):
    return {"id_bitacora": r["id_bitacora"], **parsear(r["accion"], r["detalle"]), "fecha": r["fecha"],
            "usuario": {"matricula": r["matricula"], "nombre_completo": r["nombre_completo"]}}


def listar(canal="", q="", desde="", limite=100, id_usuario=None):
    f = validate({"canal": canal or None, "desde": desde or None}, SCHEMA)
    limite = min(max(limite, 1), LIMITE_MAX)
    return [_fila(r) for r in model.list_(f["canal"] or "", q, f["desde"], id_usuario, limite)]


def mias(id_usuario, **filtros):
    if id_usuario is None:  # visitante: sin cuenta, sin avisos
        return []
    return listar(id_usuario=id_usuario, **filtros)
