"""Capa SERVICE de info: expone las preguntas frecuentes y el estado de salud para los healthchecks (RNF-12)."""
from . import model


def faq():
    """Preguntas frecuentes publicas (PS-S3-01).

    Returns:
        list[dict]: `pregunta`, `respuesta`, `categoria`.
    """
    return model.faq()


def health():
    """Estado de salud del servicio para monitoreo (healthchecks de Docker, RNF-12). No lanza excepciones.

    Returns:
        tuple[dict, int]: `({"ok": True, "db": True}, 200)` si la base responde; `({"ok": False, "db": False}, 503)`
        si falla la conexion o la consulta.
    """
    try:
        return {"ok": True, "db": model.ping()}, 200
    except Exception:
        return {"ok": False, "db": False}, 503
