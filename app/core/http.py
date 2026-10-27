"""Ayudas HTTP para controladores: cuerpo JSON, parametros de consulta y respuestas."""
from flask import request


def body(strict=False):
    """Cuerpo JSON como dict. Si no es un objeto: {} (o ApiError 400 con strict=True)."""
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    if strict:
        from .errors import ApiError

        raise ApiError("El cuerpo de la petición debe ser un objeto JSON.")
    return {}


def ok(data=None, status=200, **extra):
    """Respuesta (cuerpo, status). Sin datos: {"ok": True}; `extra` se mezcla en un dict."""
    if data is None:
        data = extra or {"ok": True}
    elif extra:
        data = {**data, **extra}
    return data, status


def created(data):
    """Respuesta 201."""
    return data, 201


def _to_bool(raw):
    return raw.strip().lower() in ("1", "true")


def _to_int(default):
    def conv(raw):
        try:
            return int(raw)
        except ValueError:
            return default

    return conv


def query_args(spec):
    """Parametros de consulta tipados. spec = {nombre: valor_por_defecto | (defecto, conversor)}.

    El tipo se infiere del defecto: str -> texto, bool -> "1"/"true", int -> entero
    (invalido = defecto). Nunca lanza error: los filtros son opcionales.
    """
    out = {}
    for name, rule in spec.items():
        default, conv = rule if isinstance(rule, tuple) else (rule, None)
        raw = request.args.get(name)
        if raw is None:
            out[name] = default
        elif conv:
            out[name] = conv(raw)
        elif isinstance(default, bool):
            out[name] = _to_bool(raw)
        elif isinstance(default, int):
            out[name] = _to_int(default)(raw)
        else:
            out[name] = raw
    return out
