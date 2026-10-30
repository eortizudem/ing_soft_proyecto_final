"""Controlador de `inicio` (capa controller MVC): endpoint HTTP `/api/stats` del tablero."""

from app.core.auth import login_required

from . import bp, service


@bp.get("/api/stats")
@login_required
def stats():
    """GET /api/stats — estadísticas del tablero. Requiere sesión (sin permiso específico).
    Respuesta: `mio` para todos; el personal recibe además los conteos globales y el presupuesto.
    """
    return service.stats()
