from app.core import repo

_BASE = """
SELECT s.id_solicitud, s.folio, s.justificacion, s.destinatario, s.fecha, s.total_estimado, s.estado,
       s.factura_folio, s.factura_total, s.fecha_recepcion, u.nombre_completo AS solicitante
FROM solicitud_compra s JOIN usuario u ON u.id_usuario = s.id_usuario
"""


def _with_detalles(rows):
    for r in rows:
        r["detalles"] = repo.fetch_all(
            """SELECT id_detalle, descripcion, id_libro, cantidad, cantidad_recibida, precio_unitario,
                      (cantidad * precio_unitario) AS subtotal
               FROM detalle_solicitud WHERE id_solicitud = %s ORDER BY id_detalle""", (r["id_solicitud"],))
    return rows


def list_():
    return _with_detalles(repo.fetch_all(_BASE + " ORDER BY s.id_solicitud DESC"))


def get(id_solicitud):
    rows = _with_detalles(repo.fetch_all(_BASE + " WHERE s.id_solicitud = %s", (id_solicitud,)))
    return rows[0] if rows else None


def next_folio():
    repo.execute("SELECT pg_advisory_xact_lock(7002)")
    n = repo.fetch_one("SELECT COALESCE(max(substring(folio from '[0-9]+$')::int), 0) + 1 AS n "
                    "FROM solicitud_compra")["n"]
    return f"SOL{n:03d}"


def insert(folio, id_usuario, justificacion, destinatario, total):
    return repo.insert("solicitud_compra", {
        "folio": folio, "id_usuario": id_usuario, "justificacion": justificacion,
        "destinatario": destinatario, "total_estimado": total}, returning="id_solicitud")["id_solicitud"]


def insert_detalle(id_solicitud, descripcion, cantidad, precio):
    libro = repo.fetch_one("SELECT id_libro FROM libro WHERE lower(titulo) = lower(%s) ORDER BY id_libro LIMIT 1",
                           (descripcion,))
    repo.insert("detalle_solicitud", {
        "id_solicitud": id_solicitud, "id_libro": libro["id_libro"] if libro else None,
        "descripcion": descripcion, "cantidad": cantidad, "precio_unitario": precio}, returning=None)


def set_estado(id_solicitud, estado):
    repo.update("solicitud_compra", "id_solicitud", id_solicitud, {"estado": estado}, returning=None)


def usado_mes(mes):
    """Suma de total_estimado de solicitudes no canceladas con fecha en el mes (date, primer dia). D-22."""
    return repo.fetch_one(
        """SELECT COALESCE(sum(total_estimado), 0) AS t FROM solicitud_compra
           WHERE estado <> 'cancelada' AND date_trunc('month', fecha) = date_trunc('month', %s::date)""",
        (mes,))["t"]


def lock_presupuesto():
    repo.execute("SELECT pg_advisory_xact_lock(7003)")


def hoy():
    return repo.fetch_one("SELECT CURRENT_DATE AS d")["d"]


def total_recibido(id_solicitud):
    return repo.fetch_one("SELECT COALESCE(sum(cantidad_recibida), 0) AS n FROM detalle_solicitud WHERE id_solicitud = %s",
                          (id_solicitud,))["n"]


def lock_detalles(id_solicitud):
    return repo.fetch_all(
        """SELECT id_detalle, descripcion, id_libro, cantidad, cantidad_recibida FROM detalle_solicitud
           WHERE id_solicitud = %s ORDER BY id_detalle FOR UPDATE""", (id_solicitud,))


def sumar_recibido(id_detalle, n):
    repo.execute("UPDATE detalle_solicitud SET cantidad_recibida = cantidad_recibida + %s WHERE id_detalle = %s",
                 (n, id_detalle))


def registrar_factura(id_solicitud, folio, total, completa, fecha):
    """Folio de la ultima factura; total acumulado de facturas; fecha_recepcion solo al completar."""
    repo.execute(
        """UPDATE solicitud_compra SET factura_folio = %s, factura_total = COALESCE(factura_total, 0) + %s,
               estado = CASE WHEN %s THEN 'recibida' ELSE estado END,
               fecha_recepcion = CASE WHEN %s THEN %s ELSE fecha_recepcion END
           WHERE id_solicitud = %s""", (folio, total, completa, completa, fecha, id_solicitud))
