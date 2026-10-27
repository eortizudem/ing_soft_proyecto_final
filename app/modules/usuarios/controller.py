from app.core.auth import current_user, permission_required
from app.core.http import body, created, query_args

from . import bp, service


@bp.get("/api/usuarios")
@permission_required("usuarios")
def listar():
    return service.listar(**query_args({"q": "", "rol": "", "estado": "", "limite": 0}))


@bp.get("/api/usuarios/<int:id_usuario>")
@permission_required("usuarios")
def obtener(id_usuario):
    return service.obtener(id_usuario)


@bp.post("/api/usuarios")
@permission_required("usuarios")
def crear():
    return created(service.crear(body(), current_user()))


@bp.put("/api/usuarios/<int:id_usuario>")
@permission_required("usuarios")
def actualizar(id_usuario):
    return service.actualizar(id_usuario, body(), current_user())


@bp.post("/api/usuarios/<int:id_usuario>/toggle")
@permission_required("usuarios")
def toggle(id_usuario):
    return service.alternar(id_usuario, current_user())


@bp.get("/api/usuarios/<int:id_usuario>/historial")
@permission_required("usuarios")
def historial(id_usuario):
    return service.historial(id_usuario)


@bp.get("/api/usuarios/actualizar")
@permission_required("usuarios")
def actualizacion_vista():
    return service.previsualizar_actualizacion()


@bp.post("/api/usuarios/actualizar")
@permission_required("usuarios")
def actualizacion_aplicar():
    return service.actualizar_lista(current_user())


@bp.post("/api/usuarios/importar")
@permission_required("usuarios")
def importar():
    return service.importar_csv(body().get("csv"), current_user())
