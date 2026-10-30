"""Capa CONTROLLER (HTTP) de info: endpoints publicos `/api/faq` y `/api/health`. Delega en `service.py`."""
from . import bp, service


@bp.get("/api/faq")
def faq():
    """GET /api/faq. Permiso: ninguno (publico). Respuesta 200: lista de `{pregunta, respuesta, categoria}`."""
    return service.faq()


@bp.get("/api/health")
def health():
    """GET /api/health. Permiso: ninguno (publico, usado por healthchecks). Respuesta 200 `{ok: true, db: true}`;
    503 `{ok: false, db: false}` si la base de datos no responde.
    """
    return service.health()
