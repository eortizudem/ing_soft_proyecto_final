"""SQL de prestamos (via core/repo). Las decisiones de negocio viven en core/circulacion y en service.py."""
from app.core import consultas, repo

# "estado" se calcula con la definicion unica de vencido (D-24); prestamo.estado es solo un cache.
_BASE = """
SELECT * FROM (
  SELECT p.id_prestamo, 'PRE-' || lpad(p.id_prestamo::text, 6, '0') AS folio,
    u.id_usuario, u.matricula, u.nombre_completo, r.nombre AS rol,
    l.id_libro, l.clave, l.titulo,
    p.id_ejemplar, e.numero_copia, p.fecha_prestamo, p.fecha_vencimiento, p.fecha_devolucion,
    CASE WHEN p.fecha_devolucion IS NOT NULL THEN 'devuelto'
         WHEN p.fecha_vencimiento < CURRENT_DATE THEN 'vencido' ELSE 'activo' END AS estado,
    p.num_renovaciones, pol.max_renovaciones, pol.multa_diaria, pol.dias_prestamo, p.id_politica
  FROM prestamo p
  JOIN usuario u ON u.id_usuario = p.id_usuario JOIN rol r ON r.id_rol = u.id_rol
  JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar JOIN libro l ON l.id_libro = e.id_libro
  JOIN politica_prestamo pol ON pol.id_politica = p.id_politica
) t
"""

_POLITICAS = """
SELECT pol.id_politica, r.nombre AS rol, pol.dias_prestamo, pol.max_libros, pol.max_renovaciones,
  pol.multa_diaria, pol.activa
FROM politica_prestamo pol JOIN rol r ON r.id_rol = pol.id_rol
"""


def list_(estado="", q="", matricula="", limite=None):
    return repo.select(_BASE, {"t.estado": estado, "t.matricula": matricula},
                       search=(q, ["t.folio", "t.matricula", "t.nombre_completo", "t.clave", "t.titulo"]),
                       order="t.id_prestamo DESC", limit=repo.tope(limite))


def get(id_prestamo):
    return repo.fetch_one(_BASE + " WHERE t.id_prestamo = %s", (id_prestamo,))


def renovaciones(id_prestamo):
    return repo.fetch_all("SELECT fecha, nueva_fecha_vencimiento FROM renovacion WHERE id_prestamo = %s "
                          "ORDER BY id_renovacion", (id_prestamo,))


def adeudos(id_prestamo):
    return repo.fetch_all("SELECT id_adeudo, tipo, monto, estado FROM adeudo WHERE id_prestamo = %s "
                          "ORDER BY id_adeudo", (id_prestamo,))


def lock_usuario(id_usuario):
    """Serializa los prestamos de un mismo usuario (limite de ejemplares bajo concurrencia)."""
    repo.fetch_one("SELECT id_usuario FROM usuario WHERE id_usuario = %s FOR UPDATE", (id_usuario,))


def find_libro(clave=None, id_libro=None):
    if id_libro:
        return repo.fetch_one("SELECT id_libro, clave FROM libro WHERE id_libro = %s", (id_libro,))
    return consultas.libro_por_clave(clave)


def lock_prestamo(id_prestamo):
    return repo.fetch_one(
        "SELECT p.*, e.id_libro FROM prestamo p JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar "
        "WHERE p.id_prestamo = %s FOR UPDATE OF p", (id_prestamo,))


def take_ejemplar(id_libro):
    """Ejemplar disponible bloqueado (SKIP LOCKED: dos prestamos simultaneos no toman el mismo)."""
    return repo.fetch_one("SELECT id_ejemplar FROM ejemplar WHERE id_libro = %s AND estado = 'disponible' "
                          "ORDER BY numero_copia LIMIT 1 FOR UPDATE SKIP LOCKED", (id_libro,))


def set_ejemplar(id_ejemplar, estado, solo_si=None):
    cond = " AND estado = %s" if solo_si else ""
    return repo.execute(f"UPDATE ejemplar SET estado = %s WHERE id_ejemplar = %s{cond}",
                        (estado, id_ejemplar) + ((solo_si,) if solo_si else ()))


def insert_prestamo(id_ejemplar, id_usuario, id_politica, vencimiento):
    return repo.insert("prestamo", {"id_ejemplar": id_ejemplar, "id_usuario": id_usuario, "id_politica": id_politica,
                                    "fecha_vencimiento": vencimiento}, returning="id_prestamo")["id_prestamo"]


def recoger_espera(id_usuario, id_libro):
    """lista_espera: el usuario notificado recoge el libro (contrato con B)."""
    repo.execute("UPDATE lista_espera SET estado = 'recogido' WHERE id_usuario = %s AND id_libro = %s "
                 "AND estado = 'notificado'", (id_usuario, id_libro))


def renovar(id_prestamo, num_renovaciones, nueva_fecha):
    repo.update("prestamo", "id_prestamo", id_prestamo,
                {"fecha_vencimiento": nueva_fecha, "num_renovaciones": num_renovaciones, "estado": "activo"},
                returning=None)
    repo.insert("renovacion", {"id_prestamo": id_prestamo, "nueva_fecha_vencimiento": nueva_fecha}, returning=None)


def insert_adeudo_retraso(id_prestamo, dias, monto):
    return repo.insert("adeudo", {"id_prestamo": id_prestamo, "tipo": "retraso", "dias_retraso": dias, "monto": monto},
                       returning="id_adeudo")["id_adeudo"]


def ubicacion_libro(id_libro):
    return repo.fetch_one("SELECT ub.planta, ub.pasillo, ub.librero, ub.nivel FROM libro l "
                          "JOIN ubicacion ub ON ub.id_ubicacion = l.id_ubicacion WHERE l.id_libro = %s", (id_libro,))


def notificaciones_recibo(folio_recibo):
    return repo.fetch_all("SELECT accion, fecha, detalle FROM bitacora WHERE accion IN ('notif_email', 'notif_whatsapp') "
                          "AND detalle LIKE %s ORDER BY id_bitacora", (f"%|Recibo de préstamo {folio_recibo}:%",))


def politicas():
    return repo.fetch_all(_POLITICAS + " ORDER BY pol.id_politica")


def politica(id_politica):
    return repo.fetch_one(_POLITICAS + " WHERE pol.id_politica = %s", (id_politica,))


def update_politica(id_politica, data):
    repo.update("politica_prestamo", "id_politica", id_politica, data, returning=None)
