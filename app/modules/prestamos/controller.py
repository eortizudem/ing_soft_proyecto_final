from app.core.auth import current_user, permission_required, require_login
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/prestamos")
@permission_required("prestamos")
def listar():
    return service.listar(**query_args({"estado": "", "q": "", "matricula": "", "limite": 0}))


@bp.post("/api/prestamos/validar")
@permission_required("prestamos")
def validar():
    return service.validar(body())


@bp.post("/api/prestamos")
@permission_required("prestamos")
def crear():
    return created(service.crear(body(), current_user()))


@bp.get("/api/prestamos/<int:id_prestamo>")
@permission_required("prestamos")
def obtener(id_prestamo):
    return service.obtener(id_prestamo)


@bp.post("/api/prestamos/<int:id_prestamo>/renovar")
@permission_required("prestamos")
def renovar(id_prestamo):
    return service.renovar(id_prestamo, current_user())


@bp.post("/api/prestamos/<int:id_prestamo>/devolver")
@permission_required("prestamos")
def devolver(id_prestamo):
    return service.devolver(id_prestamo, current_user())


@bp.get("/api/prestamos/<int:id_prestamo>/recibo")
@permission_required("prestamos")
def recibo(id_prestamo):
    return service.recibo(id_prestamo)


@bp.post("/api/prestamos/<int:id_prestamo>/recibo/enviar")
@permission_required("prestamos")
def enviar_recibo(id_prestamo):
    return service.enviar_recibo(id_prestamo, body(), current_user())


@bp.get("/api/politicas")
def politicas():
    return service.politicas(require_login())


@bp.put("/api/politicas/<int:id_politica>")
@permission_required("perfiles")
def actualizar_politica(id_politica):
    return service.actualizar_politica(id_politica, body(), current_user())
