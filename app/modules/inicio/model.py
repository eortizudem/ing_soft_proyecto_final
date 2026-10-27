from app.core import repo
from app.core.consultas import ABIERTO as _ABIERTO, VENCIDO as _VENCIDO


def stats():
    """Tablero del personal: conteos globales por SQL directo (vencido = D-24)."""
    return repo.fetch_one(
        f"""SELECT (SELECT count(*) FROM usuario WHERE estado='activo')::int AS usuarios_activos,
                  (SELECT count(*) FROM libro WHERE estado='activo')::int AS titulos_activos,
                  (SELECT count(*) FROM solicitud_compra WHERE estado='pendiente')::int AS compras_pendientes,
                  (SELECT count(*) FROM prestamo WHERE {_ABIERTO})::int AS prestamos_activos,
                  (SELECT count(*) FROM prestamo WHERE {_VENCIDO})::int
                    AS prestamos_vencidos,
                  (SELECT COALESCE(sum(monto), 0) FROM adeudo WHERE estado='pendiente') AS adeudos_pendientes,
                  (SELECT count(*) FROM lista_espera WHERE estado IN ('en_espera','notificado'))::int AS espera_activa,
                  (SELECT count(DISTINCT c.id_conversacion) FROM conversacion c
                     JOIN mensaje m ON m.id_conversacion=c.id_conversacion
                     JOIN intencion i ON i.id_intencion=m.id_intencion
                    WHERE NOT c.resuelta AND i.nombre='pasar_a_bibliotecario')::int AS consultas_pendientes""")


def mio(id_usuario):
    """Estado propio: préstamos abiertos, vencidos, adeudos pendientes (monto) y esperas activas."""
    return repo.fetch_one(
        f"""SELECT (SELECT count(*) FROM prestamo WHERE id_usuario=%(u)s AND {_ABIERTO})::int AS prestamos_activos,
                  (SELECT count(*) FROM prestamo WHERE id_usuario=%(u)s AND {_VENCIDO})::int AS prestamos_vencidos,
                  (SELECT min(fecha_vencimiento) FROM prestamo WHERE id_usuario=%(u)s AND {_ABIERTO}) AS proximo_vencimiento,
                  (SELECT COALESCE(sum(a.monto), 0) FROM adeudo a JOIN prestamo p ON p.id_prestamo=a.id_prestamo
                    WHERE p.id_usuario=%(u)s AND a.estado='pendiente') AS adeudos_pendientes,
                  (SELECT count(*) FROM lista_espera WHERE id_usuario=%(u)s
                     AND estado IN ('en_espera','notificado'))::int AS espera_activa""", {"u": id_usuario})


def usado_mes():
    """Compras no canceladas del mes en curso (USD), misma definición que `compras.presupuesto` (D-22)."""
    return repo.fetch_one(
        """SELECT COALESCE(sum(total_estimado), 0) AS t FROM solicitud_compra
           WHERE estado <> 'cancelada' AND date_trunc('month', fecha) = date_trunc('month', CURRENT_DATE)""")["t"]
