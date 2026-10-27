"""Alternar estado activo/inactivo con guardas, generico para cualquier tabla."""
from . import repo

ACTIVO, INACTIVO = "activo", "inactivo"


def toggle_estado(table, pk_col, id_, *, load, guard=None, extra=None, col="estado"):
    """Invierte `col` entre activo/inactivo.

    load(id) -> fila actual (lanza 404 si no existe; puede traer campos calculados para la guarda).
    guard(fila, nuevo_estado) puede lanzar ApiError para impedir el cambio.
    extra: {nuevo_estado: {columna: valor}} columnas adicionales por transicion.
    Devuelve (fila_anterior, nuevo_estado); la bitacora la registra el servicio (@audit).
    """
    row = load(id_)
    nuevo = INACTIVO if row[col] == ACTIVO else ACTIVO
    if guard:
        guard(row, nuevo)
    repo.update(table, pk_col, id_, {col: nuevo, **(extra or {}).get(nuevo, {})}, returning=None)
    return row, nuevo
