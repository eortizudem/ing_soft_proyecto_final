"""Capa controlador de reportes (HTTP): rutas `/api/reportes`. Requieren el permiso `reportes` (más el permiso extra por tipo).
"""

from app.core.auth import current_user, permission_required
from app.core.http import body, query_args

from . import bp, service


@bp.get("/api/reportes/<tipo>")
@permission_required("reportes")
def generar(tipo):
    """GET /api/reportes/<tipo> — genera un reporte tabular. Permiso: `reportes` (+ `usuarios` o `prestamos` según el tipo).

    Query: formato (pantalla|pdf|impresion), planta, pasillo, librero, tema, desde, hasta, incluir_docentes.
    Respuesta: {tipo, generado, generado_por, columnas, filas, total}. Errores: 400 (filtros/formato), 403, 404 (tipo).
    """
    q = query_args({"formato": "pantalla", "planta": "", "pasillo": "", "librero": "", "tema": "", "desde": "",
                    "hasta": "", "incluir_docentes": False})
    return service.generar(tipo, q.pop("formato"), current_user(), q)


@bp.post("/api/reportes/con_adeudos/aviso")
@permission_required("reportes")
def aviso_con_adeudos():
    """POST /api/reportes/con_adeudos/aviso — avisa a Servicios Escolares de los alumnos con adeudos (RF-28).
    Permiso: `reportes` (+ `prestamos`).

    Payload: {incluir_docentes?}. Respuesta: {enviados, matriculas}. Errores: 403, 422 si no hay adeudos.
    """
    return service.aviso_con_adeudos(current_user(), bool(body().get("incluir_docentes")))
