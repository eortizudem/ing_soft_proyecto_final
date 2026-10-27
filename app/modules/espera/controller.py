from app.core.auth import current_user, login_required, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/espera")
@permission_required("espera")
def listar():
    a = query_args({"estado": "", "id_libro": 0, "q": ""})
    return service.listar(a["estado"], a["id_libro"], a["q"])


@bp.get("/api/espera/libros")
@permission_required("espera")
def libros():
    return service.libros()


@bp.get("/api/espera/mias")
@login_required
def mias():
    return service.mias(current_user())


@bp.post("/api/espera")
@permission_required("espera")
def crear():
    return created(service.crear(body(), current_user()))


@bp.post("/api/espera/unirse")
@login_required
def unirse():
    return created(service.unirse(body(), current_user()))


@bp.delete("/api/espera/<int:id_espera>")
@login_required
def cancelar(id_espera):
    return service.cancelar(id_espera, current_user())

