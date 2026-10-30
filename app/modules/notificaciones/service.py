"""Capa SERVICE de notificaciones (reglas de negocio): valida filtros y da forma a los avisos simulados (D-11; RNF-10, PS-S2-06)."""
from app.core.notificaciones import CANALES, parsear
from app.core.validators import Date, Enum, validate

from . import model

LIMITE_MAX = 500
SCHEMA = {
    "canal": Enum(CANALES, "Selecciona un canal válido.", label="canal", required=False),
    "desde": Date(label="fecha", required=False),
}


def _fila(r):
    """Convierte una fila de bitacora en el aviso expuesto por la API.

    Args:
        r (dict): fila de `model.list_`.

    Returns:
        dict: `id_bitacora`, `canal`, `destino`, `asunto`, `cuerpo` (via `core.notificaciones.parsear`), `fecha` y
        `usuario` (`matricula`, `nombre_completo`).
    """
    return {"id_bitacora": r["id_bitacora"], **parsear(r["accion"], r["detalle"]), "fecha": r["fecha"],
            "usuario": {"matricula": r["matricula"], "nombre_completo": r["nombre_completo"]}}


def listar(canal="", q="", desde="", limite=100, id_usuario=None):
    """Lista avisos simulados con filtros (vista del personal con permiso `notificaciones`).

    Args:
        canal (str): `email`, `whatsapp`, `servicios_escolares`, `tesoreria` o vacio (todos).
        q (str): texto de busqueda (persona, destino, asunto).
        desde (str): fecha ISO minima (`AAAA-MM-DD`) o vacio.
        limite (int): maximo de avisos; se acota entre 1 y `LIMITE_MAX` (500).
        id_usuario (int | None): si se indica, solo los avisos de ese usuario.

    Returns:
        list[dict]: avisos mas recientes primero (ver `_fila`).

    Raises:
        ApiError: 400 si `canal` o `desde` no son validos.
    """
    f = validate({"canal": canal or None, "desde": desde or None}, SCHEMA)
    limite = min(max(limite, 1), LIMITE_MAX)
    return [_fila(r) for r in model.list_(f["canal"] or "", q, f["desde"], id_usuario, limite)]


def mias(id_usuario, **filtros):
    """Avisos del propio usuario (alumno o docente; RO-05). Un visitante no tiene cuenta, por lo que no recibe avisos.

    Args:
        id_usuario (int | None): usuario actual (`None` para visitante).
        **filtros: `canal`, `q`, `desde`, `limite` como en `listar`.

    Returns:
        list[dict]: avisos del usuario; lista vacia para visitante.

    Raises:
        ApiError: 400 si algun filtro es invalido.
    """
    if id_usuario is None:  # visitante: sin cuenta, sin avisos
        return []
    return listar(id_usuario=id_usuario, **filtros)
