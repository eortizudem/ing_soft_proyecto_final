"""Modelo de préstamos: acceso a datos SQL (capa model del MVC).

Consultas y escrituras sobre `prestamo`, `renovacion`, `ejemplar`, `adeudo` y
`politica_prestamo` vía `app.core.repo`. No contiene reglas de negocio: las decisiones
de circulación (RN-01..RN-06) viven en `app.core.circulacion` y en `service.py`.
"""
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
    """Lista préstamos con estado calculado (D-24), más recientes primero.

    Args:
        estado: Filtro exacto por estado calculado ('activo', 'vencido', 'devuelto'); vacío = todos.
        q: Texto libre sobre folio, matrícula, nombre, clave y título.
        matricula: Filtro exacto por matrícula del usuario.
        limite: Tope de filas; None usa el tope por defecto de `repo.tope`.

    Returns:
        list[dict]: Filas planas de `_BASE` (usuario y libro sin anidar).
    """
    return repo.select(_BASE, {"t.estado": estado, "t.matricula": matricula},
                       search=(q, ["t.folio", "t.matricula", "t.nombre_completo", "t.clave", "t.titulo"]),
                       order="t.id_prestamo DESC", limit=repo.tope(limite))


def get(id_prestamo):
    """Obtiene un préstamo por id con estado calculado (D-24).

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict | None: Fila plana de `_BASE`, o None si no existe.
    """
    return repo.fetch_one(_BASE + " WHERE t.id_prestamo = %s", (id_prestamo,))


def renovaciones(id_prestamo):
    """Historial de renovaciones de un préstamo.

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        list[dict]: Filas con `fecha` y `nueva_fecha_vencimiento`, en orden cronológico.
    """
    return repo.fetch_all("SELECT fecha, nueva_fecha_vencimiento FROM renovacion WHERE id_prestamo = %s "
                          "ORDER BY id_renovacion", (id_prestamo,))


def adeudos(id_prestamo):
    """Adeudos generados por un préstamo.

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        list[dict]: Filas con `id_adeudo`, `tipo`, `monto` y `estado`.
    """
    return repo.fetch_all("SELECT id_adeudo, tipo, monto, estado FROM adeudo WHERE id_prestamo = %s "
                          "ORDER BY id_adeudo", (id_prestamo,))


def lock_usuario(id_usuario):
    """Serializa los préstamos de un mismo usuario (límite de ejemplares bajo concurrencia, RN-01).

    Args:
        id_usuario: Usuario a bloquear con `FOR UPDATE` hasta el fin de la transacción.
    """
    repo.fetch_one("SELECT id_usuario FROM usuario WHERE id_usuario = %s FOR UPDATE", (id_usuario,))


def find_libro(clave=None, id_libro=None):
    """Busca un libro por id o, en su defecto, por clave.

    Args:
        clave: Clave del libro (se usa si no se da `id_libro`).
        id_libro: Identificador del libro; tiene prioridad sobre la clave.

    Returns:
        dict | None: `id_libro` y `clave`, o None si no existe.
    """
    if id_libro:
        return repo.fetch_one("SELECT id_libro, clave FROM libro WHERE id_libro = %s", (id_libro,))
    return consultas.libro_por_clave(clave)


def lock_prestamo(id_prestamo):
    """Obtiene un préstamo con su `id_libro` y lo bloquea (`FOR UPDATE OF p`).

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict | None: Fila de `prestamo` más `id_libro`, o None si no existe.
    """
    return repo.fetch_one(
        "SELECT p.*, e.id_libro FROM prestamo p JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar "
        "WHERE p.id_prestamo = %s FOR UPDATE OF p", (id_prestamo,))


def take_ejemplar(id_libro):
    """Ejemplar disponible bloqueado (SKIP LOCKED: dos préstamos simultáneos no toman el mismo).

    Args:
        id_libro: Libro del que se necesita un ejemplar.

    Returns:
        dict | None: `id_ejemplar` de la copia de menor número, o None si no hay disponibles.
    """
    return repo.fetch_one("SELECT id_ejemplar FROM ejemplar WHERE id_libro = %s AND estado = 'disponible' "
                          "ORDER BY numero_copia LIMIT 1 FOR UPDATE SKIP LOCKED", (id_libro,))


def set_ejemplar(id_ejemplar, estado, solo_si=None):
    """Cambia el estado de un ejemplar, opcionalmente solo si tiene un estado esperado.

    Args:
        id_ejemplar: Ejemplar a actualizar.
        estado: Nuevo estado ('prestado', 'disponible', ...).
        solo_si: Si se indica, solo actualiza cuando el estado actual coincide.

    Returns:
        Resultado de `repo.execute` (filas afectadas).
    """
    cond = " AND estado = %s" if solo_si else ""
    return repo.execute(f"UPDATE ejemplar SET estado = %s WHERE id_ejemplar = %s{cond}",
                        (estado, id_ejemplar) + ((solo_si,) if solo_si else ()))


def insert_prestamo(id_ejemplar, id_usuario, id_politica, vencimiento):
    """Inserta un préstamo nuevo.

    Args:
        id_ejemplar: Ejemplar prestado.
        id_usuario: Usuario que recibe el préstamo.
        id_politica: Política vigente aplicada (RN-05/RN-06).
        vencimiento: Fecha de vencimiento calculada en días hábiles (D-03).

    Returns:
        int: `id_prestamo` generado.
    """
    return repo.insert("prestamo", {"id_ejemplar": id_ejemplar, "id_usuario": id_usuario, "id_politica": id_politica,
                                    "fecha_vencimiento": vencimiento}, returning="id_prestamo")["id_prestamo"]


def recoger_espera(id_usuario, id_libro):
    """Marca como 'recogido' la entrada de lista de espera del usuario notificado (contrato con espera).

    Args:
        id_usuario: Usuario que se lleva el libro.
        id_libro: Libro prestado.
    """
    repo.execute("UPDATE lista_espera SET estado = 'recogido' WHERE id_usuario = %s AND id_libro = %s "
                 "AND estado = 'notificado'", (id_usuario, id_libro))


def renovar(id_prestamo, num_renovaciones, nueva_fecha):
    """Aplica una renovación: actualiza el préstamo y registra la renovación (D-05).

    Args:
        id_prestamo: Préstamo renovado.
        num_renovaciones: Nuevo contador de renovaciones.
        nueva_fecha: Nueva fecha de vencimiento.
    """
    repo.update("prestamo", "id_prestamo", id_prestamo,
                {"fecha_vencimiento": nueva_fecha, "num_renovaciones": num_renovaciones, "estado": "activo"},
                returning=None)
    repo.insert("renovacion", {"id_prestamo": id_prestamo, "nueva_fecha_vencimiento": nueva_fecha}, returning=None)


def insert_adeudo_retraso(id_prestamo, dias, monto):
    """Inserta un adeudo de tipo 'retraso' (RN-03, D-04).

    Args:
        id_prestamo: Préstamo devuelto con retraso.
        dias: Días hábiles de retraso.
        monto: Multa calculada en MXN.

    Returns:
        int: `id_adeudo` generado.
    """
    return repo.insert("adeudo", {"id_prestamo": id_prestamo, "tipo": "retraso", "dias_retraso": dias, "monto": monto},
                       returning="id_adeudo")["id_adeudo"]


def ubicacion_libro(id_libro):
    """Ubicación física del libro (para el recibo, RF-19).

    Args:
        id_libro: Identificador del libro.

    Returns:
        dict | None: `planta`, `pasillo`, `librero` y `nivel`, o None si no tiene ubicación.
    """
    return repo.fetch_one("SELECT ub.planta, ub.pasillo, ub.librero, ub.nivel FROM libro l "
                          "JOIN ubicacion ub ON ub.id_ubicacion = l.id_ubicacion WHERE l.id_libro = %s", (id_libro,))


def notificaciones_recibo(folio_recibo):
    """Avisos de recibo enviados (email/WhatsApp simulados en bitácora, D-11).

    Args:
        folio_recibo: Folio del recibo (p. ej. 'REC-000012').

    Returns:
        list[dict]: Filas de `bitacora` con `accion`, `fecha` y `detalle`.
    """
    return repo.fetch_all("SELECT accion, fecha, detalle FROM bitacora WHERE accion IN ('notif_email', 'notif_whatsapp') "
                          "AND detalle LIKE %s ORDER BY id_bitacora", (f"%|Recibo de préstamo {folio_recibo}:%",))


def politicas():
    """Lista todas las políticas de préstamo con su rol.

    Returns:
        list[dict]: `id_politica`, `rol`, `dias_prestamo`, `max_libros`, `max_renovaciones`, `multa_diaria`, `activa`.
    """
    return repo.fetch_all(_POLITICAS + " ORDER BY pol.id_politica")


def politica(id_politica):
    """Obtiene una política de préstamo por id.

    Args:
        id_politica: Identificador de la política.

    Returns:
        dict | None: Fila de `_POLITICAS`, o None si no existe.
    """
    return repo.fetch_one(_POLITICAS + " WHERE pol.id_politica = %s", (id_politica,))


def update_politica(id_politica, data):
    """Actualiza campos de una política de préstamo.

    Args:
        id_politica: Política a modificar.
        data: Campos ya validados (`dias_prestamo`, `max_libros`, `max_renovaciones`, `multa_diaria`).
    """
    repo.update("politica_prestamo", "id_politica", id_politica, data, returning=None)
