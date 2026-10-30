"""Controlador de préstamos: endpoints HTTP (capa controller del MVC).

Rutas bajo `/api/prestamos` y `/api/politicas`. Solo delega en `service`; el permiso
requerido se declara con `permission_required`/`require_login`.
"""
from app.core.auth import current_user, permission_required, require_login
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/prestamos")
@permission_required("prestamos")
def listar():
    """GET /api/prestamos — lista préstamos (permiso `prestamos`).

    Query: `estado`, `q`, `matricula`, `limite`.

    Returns:
        JSON: lista de préstamos.
    """
    return service.listar(**query_args({"estado": "", "q": "", "matricula": "", "limite": 0}))


@bp.post("/api/prestamos/validar")
@permission_required("prestamos")
def validar():
    """POST /api/prestamos/validar — valida RN-01 sin escribir (permiso `prestamos`, RF-17/RF-18).

    Body: `matricula`, `clave` o `id_libro`.

    Returns:
        JSON 200: `autorizado`, `motivos`, `usuario`, `libro`, `fecha_vencimiento_estimada`.
        Errores: 400 payload inválido.
    """
    return service.validar(body())


@bp.post("/api/prestamos")
@permission_required("prestamos")
def crear():
    """POST /api/prestamos — registra un préstamo (permiso `prestamos`).

    Body: `matricula`, `clave` o `id_libro`, `canales` opcional.

    Returns:
        JSON 201: `prestamo` y `recibo`. Errores: 400 payload inválido; 422 con `motivos` (RN-01).
    """
    return created(service.crear(body(), current_user()))


@bp.get("/api/prestamos/<int:id_prestamo>")
@permission_required("prestamos")
def obtener(id_prestamo):
    """GET /api/prestamos/<id_prestamo> — detalle con renovaciones y adeudos (permiso `prestamos`).

    Returns:
        JSON: préstamo. Errores: 404.
    """
    return service.obtener(id_prestamo)


@bp.post("/api/prestamos/<int:id_prestamo>/renovar")
@permission_required("prestamos")
def renovar(id_prestamo):
    """POST /api/prestamos/<id_prestamo>/renovar — renueva el préstamo (permiso `prestamos`).

    Returns:
        JSON: `prestamo` y `renovacion`. Errores: 404; 422 con `motivos` (RN-02/RN-06).
    """
    return service.renovar(id_prestamo, current_user())


@bp.post("/api/prestamos/<int:id_prestamo>/devolver")
@permission_required("prestamos")
def devolver(id_prestamo):
    """POST /api/prestamos/<id_prestamo>/devolver — registra la devolución (permiso `prestamos`).

    Returns:
        JSON: `prestamo`, `dias_retraso`, `adeudo`, `espera_notificada`. Errores: 404; 409 ya devuelto.
    """
    return service.devolver(id_prestamo, current_user())


@bp.get("/api/prestamos/<int:id_prestamo>/recibo")
@permission_required("prestamos")
def recibo(id_prestamo):
    """GET /api/prestamos/<id_prestamo>/recibo — datos del recibo (permiso `prestamos`, RF-19).

    Returns:
        JSON: recibo con avisos enviados. Errores: 404.
    """
    return service.recibo(id_prestamo)


@bp.post("/api/prestamos/<int:id_prestamo>/recibo/enviar")
@permission_required("prestamos")
def enviar_recibo(id_prestamo):
    """POST /api/prestamos/<id_prestamo>/recibo/enviar — reenvía el recibo (permiso `prestamos`).

    Body: `canales` (lista con 'email' y/o 'whatsapp').

    Returns:
        JSON: `{"enviados": [...]}`. Errores: 400 canales inválidos; 404.
    """
    return service.enviar_recibo(id_prestamo, body(), current_user())


@bp.get("/api/politicas")
def politicas():
    """GET /api/politicas — lista políticas de préstamo (sesión iniciada con permiso `prestamos` o `perfiles`).

    Returns:
        JSON: lista de políticas. Errores: 401 sin sesión; 403 sin permiso.
    """
    return service.politicas(require_login())


@bp.put("/api/politicas/<int:id_politica>")
@permission_required("perfiles")
def actualizar_politica(id_politica):
    """PUT /api/politicas/<id_politica> — edita una política (permiso `perfiles`).

    Body: `dias_prestamo`, `max_libros`, `max_renovaciones`, `multa_diaria`.

    Returns:
        JSON: política actualizada. Errores: 400 valores fuera de rango; 404.
    """
    return service.actualizar_politica(id_politica, body(), current_user())
