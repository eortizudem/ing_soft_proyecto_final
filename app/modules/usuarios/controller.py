"""Controlador de `usuarios` (capa controller MVC): endpoints HTTP bajo `/api/usuarios`.

Todos exigen el permiso `usuarios` (401 sin sesión, 403 sin permiso). Delegan en `service`.
"""

from app.core.auth import current_user, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/usuarios")
@permission_required("usuarios")
def listar():
    """GET /api/usuarios — lista cuentas. Query: q, rol, estado, limite. Respuesta: lista de cuentas."""
    return service.listar(**query_args({"q": "", "rol": "", "estado": "", "limite": 0}))


@bp.get("/api/usuarios/<int:id_usuario>")
@permission_required("usuarios")
def obtener(id_usuario):
    """GET /api/usuarios/<id_usuario> — detalle de una cuenta. Errores: 404 si no existe."""
    return service.obtener(id_usuario)


@bp.post("/api/usuarios")
@permission_required("usuarios")
def crear():
    """POST /api/usuarios — alta de cuenta. Payload: matricula, nombre_completo, correo, rol, estado,
    fuente_validacion, password. Respuesta: 201 con la cuenta. Errores: 400 (validación, duplicados).
    """
    return created(service.crear(body(), current_user()))


@bp.put("/api/usuarios/<int:id_usuario>")
@permission_required("usuarios")
def actualizar(id_usuario):
    """PUT /api/usuarios/<id_usuario> — edita una cuenta (password opcional). Respuesta: cuenta actualizada.
    Errores: 400 (validación, reglas de cuenta propia/último admin), 404.
    """
    return service.actualizar(id_usuario, body(), current_user())


@bp.post("/api/usuarios/<int:id_usuario>/toggle")
@permission_required("usuarios")
def toggle(id_usuario):
    """POST /api/usuarios/<id_usuario>/toggle — da de baja o reactiva. Respuesta: cuenta actualizada.
    Errores: 400 (baja con préstamos/multas, cuenta propia, último admin), 404.
    """
    return service.alternar(id_usuario, current_user())


@bp.get("/api/usuarios/<int:id_usuario>/historial")
@permission_required("usuarios")
def historial(id_usuario):
    """GET /api/usuarios/<id_usuario>/historial — historial (RF-04). Respuesta: prestamos, renovaciones,
    adeudos, espera y bitacora. Errores: 404.
    """
    return service.historial(id_usuario)


@bp.get("/api/usuarios/actualizar")
@permission_required("usuarios")
def actualizacion_vista():
    """GET /api/usuarios/actualizar — vista previa de la actualización desde Servicios Escolares
    simulado (D-23). Respuesta: origen, registros y resumen.
    """
    return service.previsualizar_actualizacion()


@bp.post("/api/usuarios/actualizar")
@permission_required("usuarios")
def actualizacion_aplicar():
    """POST /api/usuarios/actualizar — aplica la actualización desde Servicios Escolares simulado.
    Respuesta: creados, actualizados, bajas, omitidos y credenciales_iniciales.
    """
    return service.actualizar_lista(current_user())


@bp.post("/api/usuarios/importar")
@permission_required("usuarios")
def importar():
    """POST /api/usuarios/importar — importa lista de alumnos. Payload: {csv: str}. Respuesta: creados,
    actualizados, bajas, errores y credenciales_iniciales. Errores: 400 si el CSV está vacío.
    """
    return service.importar_csv(body().get("csv"), current_user())
