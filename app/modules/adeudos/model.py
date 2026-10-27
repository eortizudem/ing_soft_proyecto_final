"""SQL de adeudos, prestamos (cierre por perdida/daño) y ejemplares (baja)."""
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
    return nest(nest(row, "usuario", _USUARIO), "libro", _LIBRO) if row else None


def list_(estado="", tipo="", q="", matricula="", limite=None):
    rows = repo.select(_BASE, {"a.estado": estado, "a.tipo": tipo, "u.matricula": matricula.upper()},
                       search=(q, ["u.matricula", "u.nombre_completo", "l.titulo", "l.clave"]),
                       order=["a.id_adeudo DESC"], limit=repo.tope(limite))
    return [_shape(r) for r in rows]


def get(id_adeudo):
    return _shape(repo.fetch_one(_BASE + " WHERE a.id_adeudo = %s", (id_adeudo,)))


def bitacora_de(accion, id_adeudo):
    """Ultima entrada de bitacora (pago/cancelación) del adeudo; el detalle empieza con 'adeudo <id>: '."""
    return repo.fetch_one("SELECT detalle, fecha FROM bitacora WHERE accion = %s AND detalle LIKE %s "
                          "ORDER BY id_bitacora DESC LIMIT 1", (accion, f"adeudo {int(id_adeudo)}: %"))


def mark_paid(id_adeudo, fecha_pago):
    """Pendiente -> pagado de forma atomica; None si ya no estaba pendiente."""
    return repo.fetch_one("UPDATE adeudo SET estado='pagado', fecha_pago=%s "
                          "WHERE id_adeudo=%s AND estado='pendiente' RETURNING id_adeudo", (fecha_pago, id_adeudo))


def mark_cancelled(id_adeudo):
    return repo.fetch_one("UPDATE adeudo SET estado='cancelado' "
                          "WHERE id_adeudo=%s AND estado='pendiente' RETURNING id_adeudo", (id_adeudo,))


def lock_loan(id_prestamo):
    """Prestamo con usuario, libro, ejemplar y politica, bloqueado (FOR UPDATE OF p, e)."""
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
    repo.update("ejemplar", "id_ejemplar", id_ejemplar, {"estado": estado, "motivo_baja": motivo_baja}, returning=None)


def add_debt(id_prestamo, tipo, monto, dias_retraso=0):
    return repo.insert("adeudo", {"id_prestamo": id_prestamo, "tipo": tipo, "monto": monto,
                                  "dias_retraso": dias_retraso}, returning="*")
