from app.core.auth import current_user, permission_required
from app.core.http import body, query_args

from . import bp, service


@bp.get("/api/reportes/<tipo>")
@permission_required("reportes")
def generar(tipo):
    q = query_args({"formato": "pantalla", "planta": "", "pasillo": "", "librero": "", "tema": "", "desde": "",
                    "hasta": "", "incluir_docentes": False})
    return service.generar(tipo, q.pop("formato"), current_user(), q)


@bp.post("/api/reportes/con_adeudos/aviso")
@permission_required("reportes")
def aviso_con_adeudos():
    return service.aviso_con_adeudos(current_user(), bool(body().get("incluir_docentes")))
