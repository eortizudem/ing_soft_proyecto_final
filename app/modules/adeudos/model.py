"""Modelo de adeudos: acceso a datos SQL (capa model del MVC).

Consultas y escrituras sobre `adeudo`, más el bloqueo de préstamos y la baja de
ejemplares necesarios para registrar pérdida o daño. Sin reglas de negocio (están en `service.py`).
"""
from app.core import repo
from app.core.serializers import nest

_BASE = """
SELECT a.id_adeudo, a.tipo, a.monto, a.estado, a.dias_retraso, a.fecha_pago, a.id_prestamo,
  u.id_usuario, u.matricula, u.nombre_completo, r.nombre AS rol,
  l.id_libro, l.clave, l.titulo
FROM adeudo a
JOIN prestamo p ON p.id_prestamo = a.id_prestamo
JOIN usuario u ON u.id_usuario = p.id_usuario
JOIN rol r ON r.id_rol = u.id_rol
JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar
JOIN libro l ON l.id_libro = e.id_libro
"""
_USUARIO = ("id_usuario", "matricula", "nombre_completo", "rol")
_LIBRO = ("id_libro", "clave", "titulo")


def _shape(row):
    """Anida `usuario` y `libro` en una fila plana de `_BASE`.

    Args:
        row: Fila plana del adeudo o None.

    Returns:
        dict | None: Adeudo con `usuario` y `libro` anidados, o None si `row` es None.
    """
    return nest(nest(row, "usuario", _USUARIO), "libro", _LIBRO) if row else None


def list_(estado="", tipo="", q="", matricula="", limite=None):
    """Lista adeudos, más recientes primero.

    Args:
        estado: Filtro por estado ('pendiente', 'pagado', 'cancelado'); vacío = todos.
        tipo: Filtro por tipo ('retraso', 'danio', 'perdida'); vacío = todos.
        q: Texto libre sobre matrícula, nombre, título y clave.
        matricula: Matrícula exacta (se normaliza a mayúsculas).
        limite: Tope de filas; None usa el tope por defecto.

    Returns:
        list[dict]: Adeudos con `usuario` y `libro` anidados.
    """
    rows = repo.select(_BASE, {"a.estado": estado, "a.tipo": tipo, "u.matricula": matricula.upper()},
                       search=(q, ["u.matricula", "u.nombre_completo", "l.titulo", "l.clave"]),
                       order=["a.id_adeudo DESC"], limit=repo.tope(limite))
    return [_shape(r) for r in rows]


def get(id_adeudo):
    """Obtiene un adeudo por id.

    Args:
        id_adeudo: Identificador del adeudo.

    Returns:
        dict | None: Adeudo anidado, o None si no existe.
    """
    return _shape(repo.fetch_one(_BASE + " WHERE a.id_adeudo = %s", (id_adeudo,)))


def bitacora_de(accion, id_adeudo):
    """Última entrada de bitácora (pago/cancelación) del adeudo; el detalle empieza con 'adeudo <id>: '.

    Args:
        accion: Acción de bitácora ('adeudo_pago' o 'adeudo_cancelar').
        id_adeudo: Identificador del adeudo.

    Returns:
        dict | None: `detalle` y `fecha`, o None si no hay registro.
    """
    return repo.fetch_one("SELECT detalle, fecha FROM bitacora WHERE accion = %s AND detalle LIKE %s "
                          "ORDER BY id_bitacora DESC LIMIT 1", (accion, f"adeudo {int(id_adeudo)}: %"))


def mark_paid(id_adeudo, fecha_pago):
    """Pendiente -> pagado de forma atómica; None si ya no estaba pendiente (D-10).

    Args:
        id_adeudo: Adeudo a pagar.
        fecha_pago: Fecha de pago registrada.

    Returns:
        dict | None: `id_adeudo` si se actualizó, None si no estaba pendiente.
    """
    return repo.fetch_one("UPDATE adeudo SET estado='pagado', fecha_pago=%s "
                          "WHERE id_adeudo=%s AND estado='pendiente' RETURNING id_adeudo", (fecha_pago, id_adeudo))


def mark_cancelled(id_adeudo):
    """Pendiente -> cancelado de forma atómica; None si ya no estaba pendiente (D-04).

    Args:
        id_adeudo: Adeudo a cancelar.

    Returns:
        dict | None: `id_adeudo` si se actualizó, None si no estaba pendiente.
    """
    return repo.fetch_one("UPDATE adeudo SET estado='cancelado' "
                          "WHERE id_adeudo=%s AND estado='pendiente' RETURNING id_adeudo", (id_adeudo,))


def lock_loan(id_prestamo):
    """Préstamo con usuario, libro, ejemplar y política, bloqueado (FOR UPDATE OF p, e).

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict | None: Datos del préstamo (incluye `multa_diaria`, matrícula, título, copia), o None.
    """
    return repo.fetch_one("""
        SELECT p.id_prestamo, p.id_ejemplar, p.id_usuario, p.fecha_vencimiento, p.fecha_devolucion, p.estado,
          pol.multa_diaria, u.matricula, u.nombre_completo, e.numero_copia, l.id_libro, l.clave, l.titulo
        FROM prestamo p
        JOIN politica_prestamo pol ON pol.id_politica = p.id_politica
        JOIN usuario u ON u.id_usuario = p.id_usuario
        JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar
        JOIN libro l ON l.id_libro = e.id_libro
        WHERE p.id_prestamo = %s FOR UPDATE OF p, e""", (id_prestamo,))


def set_copy(id_ejemplar, estado, motivo_baja=None):
    """Cambia el estado de un ejemplar (p. ej. baja por pérdida o daño, D-07/D-08).

    Args:
        id_ejemplar: Ejemplar a actualizar.
        estado: Nuevo estado ('baja', 'disponible', ...).
        motivo_baja: 'perdido', 'danado' o None.
    """
    repo.update("ejemplar", "id_ejemplar", id_ejemplar, {"estado": estado, "motivo_baja": motivo_baja}, returning=None)


def add_debt(id_prestamo, tipo, monto, dias_retraso=0):
    """Inserta un adeudo pendiente.

    Args:
        id_prestamo: Préstamo origen.
        tipo: 'retraso', 'danio' o 'perdida'.
        monto: Importe en MXN.
        dias_retraso: Días hábiles de retraso (solo para tipo 'retraso').

    Returns:
        dict: Fila insertada.
    """
    return repo.insert("adeudo", {"id_prestamo": id_prestamo, "tipo": tipo, "monto": monto,
                                  "dias_retraso": dias_retraso}, returning="*")
