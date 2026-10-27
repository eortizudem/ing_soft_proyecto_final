"""SQL del asistente: intenciones, FAQ, conversaciones, mensajes y consultas de solo lectura."""
from datetime import datetime

from psycopg import sql

from app.core import consultas, repo

_LIBRO_COLS = ["l.clave", "l.titulo", "l.autor", "l.editorial", "l.tema"]
_CON_BIB = consultas.CON_BIBLIOTECARIO


# ---- conocimiento ----
def intenciones():
    return {r["nombre"]: r["id_intencion"] for r in repo.fetch_all("SELECT id_intencion, nombre FROM intencion WHERE activa")}


def faqs():
    return repo.fetch_all(
        "SELECT p.id_pregunta, p.pregunta, p.respuesta, i.nombre AS intencion FROM pregunta_frecuente p "
        "JOIN intencion i ON i.id_intencion = p.id_intencion WHERE p.activa AND i.activa ORDER BY p.id_pregunta")


def roles():
    return repo.fetch_all("SELECT id_rol, nombre, descripcion FROM rol ORDER BY id_rol")


# ---- catalogo (solo lectura, misma normalizacion que repo.build_where) ----
def buscar_libros(terminos, limite=5):
    """Libros activos que contienen TODOS los terminos (titulo/autor/tema/clave/editorial, sin acentos)."""
    partes, params = [sql.SQL("l.estado = 'activo'")], []
    for t in terminos:
        w, p = repo.build_where(search=(t, _LIBRO_COLS))
        partes.append(w)
        params += p
    query = sql.SQL(
        f"""SELECT l.id_libro, l.clave, l.titulo, l.autor, u.planta, u.pasillo, u.librero, u.nivel,
                  {consultas.disponibles('l')} AS disponibles
           FROM libro l JOIN ubicacion u ON u.id_ubicacion = l.id_ubicacion
           WHERE {{}} ORDER BY disponibles DESC, l.titulo LIMIT %s""").format(sql.SQL(" AND ").join(partes))
    return repo.fetch_all(query, params + [limite])


# ---- estatus propio (lectura) ----
def prestamos_abiertos(id_usuario):
    return repo.fetch_all(
        """SELECT l.titulo, p.fecha_vencimiento, p.num_renovaciones, po.max_renovaciones, po.multa_diaria
           FROM prestamo p JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar JOIN libro l ON l.id_libro = e.id_libro
           JOIN politica_prestamo po ON po.id_politica = p.id_politica
           WHERE p.id_usuario = %s AND p.fecha_devolucion IS NULL ORDER BY p.fecha_vencimiento""", (id_usuario,))


def adeudos_pendientes(id_usuario):
    return repo.fetch_all(
        """SELECT a.tipo, a.monto, l.titulo FROM adeudo a JOIN prestamo p ON p.id_prestamo = a.id_prestamo
           JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar JOIN libro l ON l.id_libro = e.id_libro
           WHERE p.id_usuario = %s AND a.estado = 'pendiente' ORDER BY a.id_adeudo""", (id_usuario,))


# ---- conversaciones ----
def crear_conversacion(id_usuario, canal):
    return repo.insert("conversacion", {"id_usuario": id_usuario, "canal": canal}, returning="*")


def conversacion(id_conversacion):
    return repo.fetch_one("SELECT * FROM conversacion WHERE id_conversacion = %s", (id_conversacion,))


def agregar_mensaje(id_conversacion, emisor, texto, id_intencion):
    return repo.insert("mensaje", {"id_conversacion": id_conversacion, "emisor": emisor, "texto": texto,
                                   "id_intencion": id_intencion}, returning="*")


def mensajes(id_conversacion):
    return repo.fetch_all("SELECT emisor, texto, fecha FROM mensaje WHERE id_conversacion = %s "
                          "ORDER BY id_mensaje", (id_conversacion,))


def ultima_intencion_asistente(id_conversacion):
    r = repo.fetch_one(
        """SELECT i.nombre FROM mensaje m JOIN intencion i ON i.id_intencion = m.id_intencion
           WHERE m.id_conversacion = %s AND m.emisor = 'asistente' ORDER BY m.id_mensaje DESC LIMIT 1""",
        (id_conversacion,))
    return r["nombre"] if r else None


def va_con_bibliotecario(id_conversacion):
    return bool(repo.fetch_one(f"SELECT 1 AS x FROM conversacion c WHERE c.id_conversacion = %s AND {_CON_BIB}",
                               (id_conversacion,)))


def valorar(id_conversacion, valores):
    return repo.update("conversacion", "id_conversacion", id_conversacion, valores, returning="*")


def resolver(id_conversacion):
    return repo.update("conversacion", "id_conversacion", id_conversacion,
                       {"resuelta": True, "fecha_fin": datetime.now()}, returning="*")


def consultas_bibliotecario(estado=""):
    resuelta = {"pendiente": False, "resuelta": True}.get(estado)
    rows = repo.fetch_all(
        f"""SELECT c.id_conversacion, c.fecha_inicio, c.resuelta, c.calificacion, u.matricula, u.nombre_completo,
                   (SELECT m.texto FROM mensaje m WHERE m.id_conversacion = c.id_conversacion
                    ORDER BY m.id_mensaje DESC LIMIT 1) AS ultimo_mensaje
            FROM conversacion c LEFT JOIN usuario u ON u.id_usuario = c.id_usuario
            WHERE {_CON_BIB} AND (%(r)s::boolean IS NULL OR c.resuelta = %(r)s)
            ORDER BY c.resuelta, c.fecha_inicio DESC, c.id_conversacion DESC""", {"r": resuelta})
    return rows
