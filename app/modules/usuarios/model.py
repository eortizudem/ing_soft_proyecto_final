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
    return repo.select(_BASE, {"r.nombre": rol, "u.estado": estado},
                       search=(q, ["u.matricula", "u.nombre_completo", "u.correo"]), order="u.matricula",
                       limit=repo.tope(limite))


def get(id_usuario):
    return repo.fetch_one(_BASE + " WHERE u.id_usuario = %s", (id_usuario,))


def get_by_matricula(matricula):
    return repo.fetch_one(_BASE + " WHERE u.matricula = %s", (matricula,))


def find_conflict(matricula, correo, exclude_id=None):
    return repo.exists("usuario", {"matricula": matricula, "correo": correo}, ci=("correo",), any_of=True,
                       exclude=("id_usuario", exclude_id))


def roles_asignables():
    return [r["nombre"] for r in repo.fetch_all("SELECT nombre FROM rol WHERE nombre <> 'visitante'")]


def count_active_admins(exclude_id=None):
    return repo.fetch_one(
        """SELECT count(*)::int AS n FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
           WHERE r.nombre = 'admin' AND u.estado = 'activo' AND u.id_usuario <> COALESCE(%s, -1)""",
        (exclude_id,),
    )["n"]


def _row(d):
    row = {"matricula": d["matricula"], "nombre_completo": d["nombre_completo"], "correo": d["correo"],
           "id_rol": repo.fetch_one("SELECT id_rol FROM rol WHERE nombre = %s", (d["rol"],))["id_rol"],
           "estado": d["estado"], "fuente_validacion": d["fuente_validacion"],
           "registro_vigente": d["registro_vigente"], "fecha_baja": d["fecha_baja"]}
    if d["password"]:  # sin contraseña nueva se conserva la actual
        row["contrasena_hash"] = d["password"]
    return row


def insert(d):
    return repo.insert("usuario", _row(d), returning="id_usuario")["id_usuario"]


def update(id_usuario, d):
    repo.update("usuario", "id_usuario", id_usuario, _row(d), returning=None)


# --- Historial (solo lectura sobre tablas de circulacion) ---
def historial_prestamos(id_usuario):
    return repo.fetch_all(
        """SELECT p.id_prestamo, l.clave AS libro_clave, l.titulo AS libro_titulo, p.fecha_prestamo,
                  p.fecha_vencimiento, p.fecha_devolucion, p.estado, p.num_renovaciones
           FROM prestamo p JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar JOIN libro l ON l.id_libro = e.id_libro
           WHERE p.id_usuario = %s ORDER BY p.fecha_prestamo DESC, p.id_prestamo DESC""", (id_usuario,))


def historial_renovaciones(id_usuario):
    return repo.fetch_all(
        """SELECT r.id_prestamo, r.fecha, r.nueva_fecha_vencimiento FROM renovacion r
           JOIN prestamo p ON p.id_prestamo = r.id_prestamo WHERE p.id_usuario = %s
           ORDER BY r.fecha DESC, r.id_renovacion DESC""", (id_usuario,))


def historial_adeudos(id_usuario):
    return repo.fetch_all(
        """SELECT a.id_adeudo, a.tipo, a.monto, a.estado, a.fecha_pago, a.id_prestamo FROM adeudo a
           JOIN prestamo p ON p.id_prestamo = a.id_prestamo WHERE p.id_usuario = %s
           ORDER BY a.id_adeudo DESC""", (id_usuario,))


def historial_espera(id_usuario):
    return repo.fetch_all(
        """SELECT w.id_espera, l.clave AS libro_clave, l.titulo AS libro_titulo, w.estado, w.posicion
           FROM lista_espera w JOIN libro l ON l.id_libro = w.id_libro WHERE w.id_usuario = %s
           ORDER BY w.fecha_solicitud DESC, w.id_espera DESC""", (id_usuario,))


def historial_bitacora(id_usuario, limit=50):
    return repo.fetch_all(
        "SELECT accion, detalle, fecha FROM bitacora WHERE id_usuario = %s ORDER BY fecha DESC, id_bitacora DESC LIMIT %s",
        (id_usuario, limit))
