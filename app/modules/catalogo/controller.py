from app.core.auth import current_user, login_required, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/libros")
@login_required
def listar():
    a = query_args({"q": "", "tema": "", "estado": "", "disponibles": False, "titulo": "", "autor": "", "clave": "",
                    "editorial": "", "clasificacion": "", "tipo_uso": "", "disponibilidad": ""})
    campos = {k: a[k] for k in ("titulo", "autor", "clave", "editorial", "clasificacion")}
    return service.listar(current_user(), a["q"], a["tema"], a["estado"], a["disponibles"], campos,
                          a["tipo_uso"], a["disponibilidad"])


@bp.get("/api/libros/pendientes")
@permission_required("catalogo")
def pendientes():
    return service.pendientes()


@bp.post("/api/libros/importar")
@permission_required("catalogo")
def importar():
    return service.importar(body(), current_user())


@bp.get("/api/libros/<int:id_libro>")
@login_required
def obtener(id_libro):
    return service.obtener(current_user(), id_libro)


@bp.post("/api/libros")
@permission_required("catalogo")
def crear():
    return created(service.crear(body(), current_user()))


@bp.put("/api/libros/<int:id_libro>")
@permission_required("catalogo")
def actualizar(id_libro):
    return service.actualizar(id_libro, body(), current_user())


@bp.post("/api/libros/<int:id_libro>/toggle")
@permission_required("catalogo")
def toggle(id_libro):
    return service.alternar(id_libro, current_user())


@bp.get("/api/temas")
@login_required
def temas():
    return service.temas(current_user())


@bp.get("/api/libros/<int:id_libro>/ejemplares")
@permission_required("catalogo")
def ejemplares(id_libro):
    return service.ejemplares(id_libro)


@bp.get("/api/libros/<int:id_libro>/etiqueta")
@permission_required("catalogo")
def etiqueta(id_libro):
    return service.etiqueta(id_libro)


@bp.post("/api/ejemplares/<int:id_ejemplar>/baja")
@permission_required("catalogo")
def baja_ejemplar(id_ejemplar):
    return service.baja_ejemplar(id_ejemplar, body(), current_user())


@bp.post("/api/ejemplares/<int:id_ejemplar>/reactivar")
@permission_required("catalogo")
def reactivar_ejemplar(id_ejemplar):
    return service.reactivar_ejemplar(id_ejemplar, current_user())
