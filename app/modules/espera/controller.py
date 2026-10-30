"""Controlador de la lista de espera: endpoints HTTP bajo `/api/espera` (capa controller del MVC).

Solo delega en `service`. Personal: permiso `espera`; autoservicio: sesión iniciada.
"""
from app.core.auth import current_user, login_required, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/espera")
@permission_required("espera")
def listar():
    """GET /api/espera — lista la espera (permiso `espera`).

    Query: `estado`, `id_libro`, `q`.

    Returns:
        JSON: lista de entradas.
    """
    a = query_args({"estado": "", "id_libro": 0, "q": ""})
    return service.listar(a["estado"], a["id_libro"], a["q"])


@bp.get("/api/espera/libros")
@permission_required("espera")
def libros():
    """GET /api/espera/libros — libros candidatos a espera con disponibilidad (permiso `espera`).

    Returns:
        JSON: lista de libros.
    """
    return service.libros()


@bp.get("/api/espera/mias")
@login_required
def mias():
    """GET /api/espera/mias — solicitudes del usuario autenticado (sesión iniciada).

    Returns:
        JSON: lista de entradas. Errores: 401 sin sesión; 403 sin cuenta de usuario.
    """
    return service.mias(current_user())


@bp.post("/api/espera")
@permission_required("espera")
def crear():
    """POST /api/espera — alta por el personal (permiso `espera`).

    Body: `matricula`, `id_libro`.

    Returns:
        JSON 201: entrada creada. Errores: 400, 404, 422 con `motivos`.
    """
    return created(service.crear(body(), current_user()))


@bp.post("/api/espera/unirse")
@login_required
def unirse():
    """POST /api/espera/unirse — el usuario se une a la espera (sesión iniciada).

    Body: `id_libro`.

    Returns:
        JSON 201: entrada creada. Errores: 400, 401, 403, 404, 422 con `motivos`.
    """
    return created(service.unirse(body(), current_user()))


@bp.delete("/api/espera/<int:id_espera>")
@login_required
def cancelar(id_espera):
    """DELETE /api/espera/<id_espera> — cancela una entrada (sesión iniciada; personal con `espera` o dueño).

    Returns:
        JSON: entrada cancelada. Errores: 401, 403, 404, 409 si ya no está activa.
    """
    return service.cancelar(id_espera, current_user())

