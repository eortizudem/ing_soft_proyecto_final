"""Capa MODEL de info (acceso a datos SQL): preguntas frecuentes y ping a la base de datos."""
from app.core import repo


def faq():
    """Preguntas frecuentes activas.

    Returns:
        list[dict]: `pregunta`, `respuesta`, `categoria`, ordenadas por id.
    """
    return repo.fetch_all("SELECT pregunta, respuesta, categoria FROM pregunta_frecuente WHERE activa "
                       "ORDER BY id_pregunta")


def ping():
    """Comprueba que la base de datos responde (`SELECT 1`).

    Returns:
        bool: `True` si responde correctamente.
    """
    return repo.fetch_one("SELECT 1 AS ok")["ok"] == 1
