"""Semilla de usuarios y datos demo de circulacion y compras (idempotente).

Los catalogos (roles, permisos, politicas, libros, FAQ...) los carga db/02_seed.sql.
Datos demo que ejercitan los modulos de circulacion (vigencias en dias habiles, core/calendario.py):
  A0512345 Maria      1 prestamo activo (LIB001) y en lista de espera de LIB005
  A0512980 Carlos     1 prestamo VENCIDO sin devolver (LIB005), estado cache 'vencido'
  A0513001 Laura      1 prestamo devuelto con retraso y un adeudo 'retraso' PENDIENTE (suspendida por RN-01)
  DOC001   Docente    3 prestamos activos (LIB001, LIB002, LIB005; limite del docente = 3)
  SOL000   compra historica 'recibida' (precio de ultima compra para la reposicion RN-04)
Uso manual: python -m app.seed
"""
from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

from .core import db
from .core.circulacion import dias_retraso, fecha_vencimiento, multa_retraso
from .core.calendario import sumar_habiles

# (matricula, nombre, correo, password, rol, fuente)
USUARIOS = [
    ("ADM001", "Andrea López", "andrea@ducky.edu.mx", "Admin123", "admin", "recursos_humanos"),
    ("A0512345", "María García", "maria@ducky.edu.mx", "Alumno123", "alumno", "servicios_escolares"),
    ("A0512980", "Carlos Ruiz", "carlos@ducky.edu.mx", "Alumno123", "alumno", "servicios_escolares"),
    ("A0513001", "Laura Méndez", "laura@ducky.edu.mx", "Alumno123", "alumno", "servicios_escolares"),
    ("CAT001", "Responsable de catálogo", "cat001@ducky.edu.mx", "Catalogo123", "catalogo", "recursos_humanos"),
    ("COM001", "Responsable de compras", "com001@ducky.edu.mx", "Compras123", "comprador", "recursos_humanos"),
    ("BIB001", "Bibliotecario", "bib001@ducky.edu.mx", "Biblioteca123", "bibliotecario", "recursos_humanos"),
    ("DOC001", "Docente", "doc001@ducky.edu.mx", "Docente123", "docente", "recursos_humanos"),
    ("COL001", "Colaborador de apoyo", "col001@ducky.edu.mx", "Colabora123", "colaborador", "recursos_humanos"),
]

# Prestamos demo: (matricula, clave, dias atras desde hoy)
PRESTAMOS = [("A0512345", "LIB001", 2), ("DOC001", "LIB001", 2), ("DOC001", "LIB002", 2), ("DOC001", "LIB005", 2),
             ("A0512980", "LIB005", 21)]


def _prestar(matricula, clave, dias_atras=2, devuelto_tarde=0):
    """Crea el prestamo con vencimiento en dias habiles. devuelto_tarde = dias habiles de retraso al devolver
    (crea el adeudo 'retraso' pendiente); con dias_atras grande y sin devolucion queda vencido."""
    ej = db.fetchone(
        """SELECT e.id_ejemplar FROM ejemplar e JOIN libro l ON l.id_libro=e.id_libro
           WHERE l.clave=%s AND e.estado='disponible' ORDER BY e.numero_copia LIMIT 1 FOR UPDATE""", (clave,))
    pol = db.fetchone(
        """SELECT u.id_usuario, p.id_politica, p.dias_prestamo, p.multa_diaria FROM usuario u
           JOIN politica_prestamo p ON p.id_rol=u.id_rol AND p.activa WHERE u.matricula=%s
           ORDER BY p.vigente_desde DESC LIMIT 1""", (matricula,))
    if not ej or not pol:
        return None
    prestado = datetime.now().replace(microsecond=0) - timedelta(days=dias_atras)
    venc = fecha_vencimiento(prestado, pol["dias_prestamo"])
    devolucion = datetime.combine(sumar_habiles(venc, devuelto_tarde), datetime.min.time()).replace(hour=12) \
        if devuelto_tarde else None
    vencido = devolucion is None and venc < date.today()
    estado = "devuelto" if devolucion else "vencido" if vencido else "activo"
    pr = db.fetchone(
        """INSERT INTO prestamo(id_ejemplar,id_usuario,id_politica,fecha_prestamo,fecha_vencimiento,fecha_devolucion,estado)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_prestamo""",
        (ej["id_ejemplar"], pol["id_usuario"], pol["id_politica"], prestado, venc, devolucion, estado))
    if not devolucion:
        db.execute("UPDATE ejemplar SET estado='prestado' WHERE id_ejemplar=%s", (ej["id_ejemplar"],))
    else:
        dias = dias_retraso(venc, devolucion)
        db.execute("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',%s,%s)",
                   (pr["id_prestamo"], dias, multa_retraso(dias, pol["multa_diaria"])))
    return pr["id_prestamo"]


def _compra(folio, comprador, justificacion, fecha, estado, lineas, extra=None):
    """Inserta una solicitud de compra demo con sus lineas `(descripcion, cantidad, precio_usd, recibida)`.

    `extra` = `(factura_folio, factura_total, fecha_recepcion)`; sin el, esos campos quedan NULL.
    """
    total = sum(c * p for _, c, p, _ in lineas)
    sol = db.fetchone(
        """INSERT INTO solicitud_compra(folio,id_usuario,justificacion,destinatario,fecha,total_estimado,estado,
             factura_folio,factura_total,fecha_recepcion)
           VALUES (%s,(SELECT id_usuario FROM usuario WHERE matricula=%s),%s,'Tesorería',%s,%s,%s,%s,%s,%s)
           RETURNING id_solicitud""", (folio, comprador, justificacion, fecha, total, estado, *(extra or (None,) * 3)))
    for desc, cant, precio, recibida in lineas:
        db.execute(
            """INSERT INTO detalle_solicitud(id_solicitud,id_libro,descripcion,cantidad,precio_unitario,cantidad_recibida)
               VALUES (%s,(SELECT id_libro FROM libro WHERE lower(titulo)=lower(%s) LIMIT 1),%s,%s,%s,%s)""",
            (sol["id_solicitud"], desc, desc, cant, precio, recibida))


def seed_if_empty(app):
    """Carga usuarios, prestamos y compras demo solo si la tabla `usuario` esta vacia (idempotente).

    Corre en una transaccion con un candado asesor (`pg_advisory_xact_lock`) para que varios procesos al arrancar
    no dupliquen la semilla; ante cualquier error hace rollback y relanza.

    Args:
        app: aplicacion Flask (se usa su contexto para obtener la conexion).

    Returns:
        True si aplico la semilla; False si ya habia usuarios.
    """
    with app.app_context():
        conn = db.get_conn()
        try:
            db.execute("SELECT pg_advisory_xact_lock(7001)")
            if db.fetchone("SELECT 1 FROM usuario LIMIT 1"):
                conn.rollback()
                return False
            for mat, nombre, correo, pw, rol, fuente in USUARIOS:
                db.execute(
                    """INSERT INTO usuario(matricula,nombre_completo,correo,contrasena_hash,id_rol,estado,
                         fuente_validacion,registro_vigente)
                       VALUES (%s,%s,%s,%s,(SELECT id_rol FROM rol WHERE nombre=%s),'activo',%s,true)""",
                    (mat, nombre, correo, generate_password_hash(pw), rol, fuente))
            for mat, clave, atras in PRESTAMOS:
                _prestar(mat, clave, atras)
            _prestar("A0513001", "LIB004", 20, devuelto_tarde=2)      # devuelto con 2 dias habiles de retraso: $20 pendiente
            db.execute(
                """INSERT INTO lista_espera(id_usuario,id_libro,posicion,estado)
                   VALUES ((SELECT id_usuario FROM usuario WHERE matricula='A0512345'),
                           (SELECT id_libro FROM libro WHERE clave='LIB005'),1,'en_espera')""")
            # SOL000: compra historica recibida (precios en USD, D-28); SOL001: solicitud pendiente de la demo
            _compra("SOL000", "COM001", "Reposición de la colección básica.", "2026-09-10", "recibida",
                    (("Ingeniería de software", 3, 42, 3), ("Clean Code", 2, 30, 2)), ("FAC-2026-001", 186, "2026-09-20"))
            _compra("SOL001", "COM001", "Actualizar la bibliografía de las materias de computación.", "2026-10-14",
                    "pendiente", (("Diseño de software", 2, 850, 0), ("Redes de computadoras", 1, 800, 0)))
            conn.commit()
            app.logger.info("Semilla de usuarios aplicada")
            return True
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    from . import create_app

    flask_app = create_app({"SKIP_SEED": True})
    print("Semilla aplicada." if seed_if_empty(flask_app) else "Ya existen usuarios; no se hizo nada.")
