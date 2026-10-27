from app.core.auth import login_required

from . import bp, service


@bp.get("/api/stats")
@login_required
def stats():
    return service.stats()
