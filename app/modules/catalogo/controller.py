"""Capa controlador del catálogo (HTTP): rutas `/api/libros`, `/api/temas` y `/api/ejemplares`.

Solo extrae parámetros/cuerpo y delega en `service`. El permiso `catalogo` protege las escrituras.
"""

from app.core.auth import current_user, login_required, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/libros")
@login_required
def listar():
    """GET /api/libros — lista/busca libros (RF-12, RF-13, RF-15). Requiere sesión.

    Query: q, tema, estado, disponibles, titulo, autor, clave, editorial, clasificacion, tipo_uso, disponibilidad.
    Respuesta: lista de libros. Sin permiso `catalogo` solo se devuelven los activos.
    """
    a = query_args({"q": "", "tema": "", "estado": "", "disponibles": False, "titulo": "", "autor": "", "clave": "",
                    "editorial": "", "clasificacion": "", "tipo_uso": "", "disponibilidad": ""})
    campos = {k: a[k] for k in ("titulo", "autor", "clave", "editorial", "clasificacion")}
    return service.listar(current_user(), a["q"], a["tema"], a["estado"], a["disponibles"], campos,
                        a["tipo_uso"], a["disponibilidad"])


@bp.get("/api/libros/pendientes")
@permission_required("catalogo")
def pendientes():
    """GET /api/libros/pendientes — líneas de compra recibidas sin catalogar (RF-06). Permiso: `catalogo`."""
    return service.pendientes()


@bp.post("/api/libros/importar")
@permission_required("catalogo")
def importar():
    """POST /api/libros/importar — alta masiva CSV (PS-S1-12). Permiso: `catalogo`.

    Payload: {csv}. Respuesta: {creados, errores[]}. Errores: 400 si el CSV está vacío o excede el máximo.
    """
    return service.importar(body(), current_user())


@bp.get("/api/libros/<int:id_libro>")
@login_required
def obtener(id_libro):
    """GET /api/libros/<id_libro> — detalle de un libro (RF-14). Requiere sesión. Error: 404 si no existe o está inactivo sin permiso."""
    return service.obtener(current_user(), id_libro)


@bp.post("/api/libros")
@permission_required("catalogo")
def crear():
    """POST /api/libros — alta de libro (RF-08..RF-10). Permiso: `catalogo`.

    Payload: ficha del libro. Respuesta: 201 con el libro. Errores: 400 (validación/clave duplicada), 404, 409 (línea de compra enlazada).
    """
    return created(service.crear(body(), current_user()))


@bp.put("/api/libros/<int:id_libro>")
@permission_required("catalogo")
def actualizar(id_libro):
    """PUT /api/libros/<id_libro> — edita el libro y su número de ejemplares. Permiso: `catalogo`.

    Respuesta: libro actualizado. Errores: 400 (validación, menos copias que prestadas, inactivar con préstamos), 404.
    """
    return service.actualizar(id_libro, body(), current_user())


@bp.post("/api/libros/<int:id_libro>/toggle")
@permission_required("catalogo")
def toggle(id_libro):
    """POST /api/libros/<id_libro>/toggle — activa/inactiva el libro (RF-11). Permiso: `catalogo`.

    Respuesta: libro actualizado. Errores: 400 si hay préstamos activos, 404.
    """
    return service.alternar(id_libro, current_user())


@bp.get("/api/temas")
@login_required
def temas():
    """GET /api/temas — temas distintos del catálogo. Requiere sesión (sin permiso `catalogo`: solo de libros activos)."""
    return service.temas(current_user())


@bp.get("/api/libros/<int:id_libro>/ejemplares")
@permission_required("catalogo")
def ejemplares(id_libro):
    """GET /api/libros/<id_libro>/ejemplares — ejemplares del libro con estado y préstamo activo (RF-11). Permiso: `catalogo`. Error: 404."""
    return service.ejemplares(id_libro)


@bp.get("/api/libros/<int:id_libro>/etiqueta")
@permission_required("catalogo")
def etiqueta(id_libro):
    """GET /api/libros/<id_libro>/etiqueta — datos de ficha y etiquetas para imprimir (RF-07). Permiso: `catalogo`. Error: 404."""
    return service.etiqueta(id_libro)


@bp.post("/api/ejemplares/<int:id_ejemplar>/baja")
@permission_required("catalogo")
def baja_ejemplar(id_ejemplar):
    """POST /api/ejemplares/<id_ejemplar>/baja — baja de ejemplar con motivo (RF-11). Permiso: `catalogo`.

    Payload: {motivo, observacion?}. Respuesta: ejemplar. Errores: 400, 404, 409 (prestado/ya de baja).
    """
    return service.baja_ejemplar(id_ejemplar, body(), current_user())


@bp.post("/api/ejemplares/<int:id_ejemplar>/reactivar")
@permission_required("catalogo")
def reactivar_ejemplar(id_ejemplar):
    """POST /api/ejemplares/<id_ejemplar>/reactivar — reactiva ejemplar dado de baja (RF-11). Permiso: `catalogo`.

    Respuesta: ejemplar. Errores: 404, 409 (no está de baja o libro inactivo).
    """
    return service.reactivar_ejemplar(id_ejemplar, current_user())
