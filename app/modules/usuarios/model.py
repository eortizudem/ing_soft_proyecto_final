"""Modelo de `usuarios` (capa model MVC): acceso a datos SQL de cuentas e historial.

Solo ejecuta consultas/escrituras vía `app.core.repo`; sin reglas de negocio (viven en `service.py`).
Los conteos de préstamos y adeudos usan las definiciones únicas de `app.core.consultas` (D-24).
"""

from app.core import consultas, repo

_BASE = f"""
SELECT u.id_usuario, u.matricula, u.nombre_completo, u.correo, r.nombre AS rol, u.estado,
  u.fuente_validacion, u.registro_vigente, u.fecha_alta, u.fecha_baja,
  {consultas.prestamos_abiertos('u')} AS prestamos_activos,
  {consultas.adeudos_monto('u')} AS adeudos_pendientes,
  {consultas.adeudos_pendientes('u')} AS adeudos_pendientes_n
FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
"""


def list_(q="", rol="", estado="", limite=None):
    """Lista cuentas con rol, préstamos abiertos y adeudos pendientes (RF-01).

    Args:
        q: Texto de búsqueda sobre matrícula, nombre o correo.
        rol: Filtro exacto por nombre de rol ('' = todos).
        estado: Filtro exacto por estado ('activo' | 'inactivo'; '' = todos).
        limite: Máximo de filas; se acota con `repo.tope`.

    Returns:
        Lista de dicts ordenada por matrícula.
    """
    return repo.select(_BASE, {"r.nombre": rol, "u.estado": estado},
                       search=(q, ["u.matricula", "u.nombre_completo", "u.correo"]), order="u.matricula",
                       limit=repo.tope(limite))


def get(id_usuario):
    """Obtiene una cuenta por id.

    Args:
        id_usuario: Identificador de la cuenta.

    Returns:
        Dict con los campos de `_BASE`, o None si no existe.
    """
    return repo.fetch_one(_BASE + " WHERE u.id_usuario = %s", (id_usuario,))


def get_by_matricula(matricula):
    """Obtiene una cuenta por matrícula (usado al sincronizar/importar, D-23).

    Args:
        matricula: Matrícula o nómina ya normalizada (mayúsculas).

    Returns:
        Dict con los campos de `_BASE`, o None si no existe.
    """
    return repo.fetch_one(_BASE + " WHERE u.matricula = %s", (matricula,))


def find_conflict(matricula, correo, exclude_id=None):
    """Indica si la matrícula o el correo (sin distinguir mayúsculas) ya los usa otra cuenta.

    Args:
        matricula: Matrícula a verificar.
        correo: Correo a verificar (comparación insensible a mayúsculas).
        exclude_id: Id de la cuenta que se edita, excluida de la comparación.

    Returns:
        True si hay conflicto con otra cuenta.
    """
    return repo.exists("usuario", {"matricula": matricula, "correo": correo}, ci=("correo",), any_of=True,
                       exclude=("id_usuario", exclude_id))


def roles_asignables():
    """Nombres de rol que se pueden asignar a una cuenta (todos salvo 'visitante', D-26).

    Returns:
        Lista de nombres de rol.
    """
    return [r["nombre"] for r in repo.fetch_all("SELECT nombre FROM rol WHERE nombre <> 'visitante'")]


def count_active_admins(exclude_id=None):
    """Cuenta administradores activos, opcionalmente excluyendo uno (regla del último administrador).

    Args:
        exclude_id: Id de cuenta a ignorar en el conteo.

    Returns:
        Número de admins activos distintos de `exclude_id`.
    """
    return repo.fetch_one(
        """SELECT count(*)::int AS n FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
           WHERE r.nombre = 'admin' AND u.estado = 'activo' AND u.id_usuario <> COALESCE(%s, -1)""",
        (exclude_id,),
    )["n"]


def _row(d):
    """Construye la fila de la tabla `usuario` a partir de los datos validados.

    Resuelve `rol` a `id_rol`; solo incluye `contrasena_hash` si hay contraseña nueva (si no, se conserva la actual).

    Args:
        d: Dict validado con matricula, nombre_completo, correo, rol, estado, fuente_validacion,
            registro_vigente, fecha_baja y password (hash o None).

    Returns:
        Dict columna -> valor listo para insertar/actualizar.
    """
    row = {"matricula": d["matricula"], "nombre_completo": d["nombre_completo"], "correo": d["correo"],
           "id_rol": repo.fetch_one("SELECT id_rol FROM rol WHERE nombre = %s", (d["rol"],))["id_rol"],
           "estado": d["estado"], "fuente_validacion": d["fuente_validacion"],
           "registro_vigente": d["registro_vigente"], "fecha_baja": d["fecha_baja"]}
    if d["password"]:  # sin contraseña nueva se conserva la actual
        row["contrasena_hash"] = d["password"]
    return row


def insert(d):
    """Inserta una cuenta nueva.

    Args:
        d: Datos validados (ver `_row`).

    Returns:
        `id_usuario` generado.
    """
    return repo.insert("usuario", _row(d), returning="id_usuario")["id_usuario"]


def update(id_usuario, d):
    """Actualiza una cuenta existente.

    Args:
        id_usuario: Cuenta a modificar.
        d: Datos validados (ver `_row`).
    """
    repo.update("usuario", "id_usuario", id_usuario, _row(d), returning=None)


# --- Historial (solo lectura sobre tablas de circulacion) ---
def historial_prestamos(id_usuario):
    """Historial de préstamos del usuario con clave y título del libro (RF-04).

    Args:
        id_usuario: Cuenta consultada.

    Returns:
        Lista de dicts, más recientes primero.
    """
    return repo.fetch_all(
        """SELECT p.id_prestamo, l.clave AS libro_clave, l.titulo AS libro_titulo, p.fecha_prestamo,
                  p.fecha_vencimiento, p.fecha_devolucion, p.estado, p.num_renovaciones
           FROM prestamo p JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar JOIN libro l ON l.id_libro = e.id_libro
           WHERE p.id_usuario = %s ORDER BY p.fecha_prestamo DESC, p.id_prestamo DESC""", (id_usuario,))


def historial_renovaciones(id_usuario):
    """Historial de renovaciones de los préstamos del usuario (RF-04).

    Args:
        id_usuario: Cuenta consultada.

    Returns:
        Lista de dicts (id_prestamo, fecha, nueva_fecha_vencimiento), más recientes primero.
    """
    return repo.fetch_all(
        """SELECT r.id_prestamo, r.fecha, r.nueva_fecha_vencimiento FROM renovacion r
           JOIN prestamo p ON p.id_prestamo = r.id_prestamo WHERE p.id_usuario = %s
           ORDER BY r.fecha DESC, r.id_renovacion DESC""", (id_usuario,))


def historial_adeudos(id_usuario):
    """Historial de adeudos (multas, daño, pérdida) del usuario (RF-04).

    Args:
        id_usuario: Cuenta consultada.

    Returns:
        Lista de dicts, más recientes primero.
    """
    return repo.fetch_all(
        """SELECT a.id_adeudo, a.tipo, a.monto, a.estado, a.fecha_pago, a.id_prestamo FROM adeudo a
           JOIN prestamo p ON p.id_prestamo = a.id_prestamo WHERE p.id_usuario = %s
           ORDER BY a.id_adeudo DESC""", (id_usuario,))


def historial_espera(id_usuario):
    """Historial de lista de espera del usuario (RF-04, D-19).

    Args:
        id_usuario: Cuenta consultada.

    Returns:
        Lista de dicts con libro, estado y posición, más recientes primero.
    """
    return repo.fetch_all(
        """SELECT w.id_espera, l.clave AS libro_clave, l.titulo AS libro_titulo, w.estado, w.posicion
           FROM lista_espera w JOIN libro l ON l.id_libro = w.id_libro WHERE w.id_usuario = %s
           ORDER BY w.fecha_solicitud DESC, w.id_espera DESC""", (id_usuario,))


def historial_bitacora(id_usuario, limit=50):
    """Últimos eventos de bitácora atribuidos al usuario (RF-04).

    Args:
        id_usuario: Cuenta consultada.
        limit: Máximo de eventos a devolver.

    Returns:
        Lista de dicts (accion, detalle, fecha), más recientes primero.
    """
    return repo.fetch_all(
        "SELECT accion, detalle, fecha FROM bitacora WHERE id_usuario = %s ORDER BY fecha DESC, id_bitacora DESC LIMIT %s",
        (id_usuario, limit))
