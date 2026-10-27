"""Serializacion JSON: date/datetime -> ISO, Decimal -> float (recursivo) y proveedor JSON de Flask."""
from datetime import date, datetime
from decimal import Decimal

from flask.json.provider import DefaultJSONProvider


def _scalar(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"No serializable: {type(o).__name__}")


def to_json(value):
    """Convierte fila(s) a tipos JSON puros (dict/list/tuple se recorren recursivamente)."""
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    if isinstance(value, (datetime, date, Decimal)):
        return _scalar(value)
    return value


def texto_ubicacion(u):
    """Ubicacion fisica -> "Planta baja · Pasillo A · Librero 01 · Nivel 1" (espejo de `location` en format.js)."""
    return f"{u['planta']} · Pasillo {u['pasillo']} · Librero {u['librero']} · Nivel {u['nivel']}" if u else ""


def nest(row, key, fields):
    """Mueve `fields` de la fila a un sub-diccionario `key` (copia; None se respeta)."""
    if row is None:
        return None
    row = dict(row)
    row[key] = {f: row.pop(f) for f in fields}
    return row


class JSONProvider(DefaultJSONProvider):
    """Los controladores devuelven dicts/listas/filas tal cual; Flask las serializa con esto."""
    ensure_ascii = False
    sort_keys = False

    @staticmethod
    def default(o):
        try:
            return _scalar(o)
        except TypeError:
            return DefaultJSONProvider.default(o)
