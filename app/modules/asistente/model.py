"""Capa MODEL del asistente (acceso a datos SQL): intenciones, FAQ, conversaciones, mensajes y consultas de solo lectura.

Solo ejecuta SQL (via `app.core.repo`); no contiene reglas de negocio ni valida permisos: eso vive en `service.py`.
Tablas: `intencion`, `pregunta_frecuente`, `rol`, `conversacion`, `mensaje`, y lecturas de `libro`, `ubicacion`,
`prestamo`, `adeudo` para el catalogo y el estatus propio (RF-30, RF-31).
"""
from datetime import datetime

from psycopg import sql

from app.core import consultas, repo

_LIBRO_COLS = ["l.clave", "l.titulo", "l.autor", "l.editorial", "l.tema"]
_CON_BIB = consultas.CON_BIBLIOTECARIO


# ---- conocimiento ----
def intenciones():
    """Intenciones activas.

    Returns:
        dict[str, int]: `{nombre: id_intencion}`.
    """
    return {r["nombre"]: r["id_intencion"] for r in repo.fetch_all("SELECT id_intencion, nombre FROM intencion WHERE activa")}


def faqs():
    """Preguntas frecuentes activas cuya intencion tambien esta activa (base de conocimiento, RF-29).

    Returns:
        list[dict]: filas con `id_pregunta`, `pregunta`, `respuesta` e `intencion` (nombre), ordenadas por id.
    """
    return repo.fetch_all(
        "SELECT p.id_pregunta, p.pregunta, p.respuesta, i.nombre AS intencion FROM pregunta_frecuente p "
        "JOIN intencion i ON i.id_intencion = p.id_intencion WHERE p.activa AND i.activa ORDER BY p.id_pregunta")


def roles():
    """Roles del sistema (para explicar la politica de prestamo a visitantes, RF-32).

    Returns:
        list[dict]: filas con `id_rol`, `nombre`, `descripcion`.
    """
    return repo.fetch_all("SELECT id_rol, nombre, descripcion FROM rol ORDER BY id_rol")


# ---- catalogo (solo lectura, misma normalizacion que repo.build_where) ----
def buscar_libros(terminos, limite=5):
    """Libros activos que contienen TODOS los terminos (titulo/autor/tema/clave/editorial, sin acentos). RF-30.

    Args:
        terminos (list[str]): terminos ya normalizados; cada uno se busca en `_LIBRO_COLS` (AND entre terminos).
        limite (int): maximo de filas (por defecto 5, `service.MAX_LIBROS`).

    Returns:
        list[dict]: `id_libro`, `clave`, `titulo`, `autor`, ubicacion (`planta`, `pasillo`, `librero`, `nivel`) y
        `disponibles` (ejemplares disponibles), ordenados por disponibilidad descendente y titulo.
    """
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
    """Prestamos sin devolver del usuario, con los datos de su politica (RF-31).

    Args:
        id_usuario (int): usuario consultado.

    Returns:
        list[dict]: `titulo`, `fecha_vencimiento`, `num_renovaciones`, `max_renovaciones`, `multa_diaria`,
        ordenados por vencimiento.
    """
    return repo.fetch_all(
        """SELECT l.titulo, p.fecha_vencimiento, p.num_renovaciones, po.max_renovaciones, po.multa_diaria
           FROM prestamo p JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar JOIN libro l ON l.id_libro = e.id_libro
           JOIN politica_prestamo po ON po.id_politica = p.id_politica
           WHERE p.id_usuario = %s AND p.fecha_devolucion IS NULL ORDER BY p.fecha_vencimiento""", (id_usuario,))


def adeudos_pendientes(id_usuario):
    """Adeudos en estado `pendiente` del usuario (RF-31).

    Args:
        id_usuario (int): usuario consultado.

    Returns:
        list[dict]: `tipo`, `monto`, `titulo` del libro, ordenados por id de adeudo.
    """
    return repo.fetch_all(
        """SELECT a.tipo, a.monto, l.titulo FROM adeudo a JOIN prestamo p ON p.id_prestamo = a.id_prestamo
           JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar JOIN libro l ON l.id_libro = e.id_libro
           WHERE p.id_usuario = %s AND a.estado = 'pendiente' ORDER BY a.id_adeudo""", (id_usuario,))


# ---- conversaciones ----
def crear_conversacion(id_usuario, canal):
    """Abre una conversacion.

    Args:
        id_usuario (int | None): dueno; `None` para visitante.
        canal (str): `web` o `movil`.

    Returns:
        dict: fila `conversacion` creada.
    """
    return repo.insert("conversacion", {"id_usuario": id_usuario, "canal": canal}, returning="*")


def conversacion(id_conversacion):
    """Obtiene una conversacion.

    Args:
        id_conversacion (int): id de la conversacion.

    Returns:
        dict | None: fila `conversacion` o `None` si no existe.
    """
    return repo.fetch_one("SELECT * FROM conversacion WHERE id_conversacion = %s", (id_conversacion,))


def agregar_mensaje(id_conversacion, emisor, texto, id_intencion):
    """Agrega un mensaje a la conversacion.

    Args:
        id_conversacion (int): conversacion destino.
        emisor (str): `usuario` o `asistente`.
        texto (str): contenido del mensaje.
        id_intencion (int | None): intencion detectada o respondida (`None` en respuestas manuales del bibliotecario).

    Returns:
        dict: fila `mensaje` creada.
    """
    return repo.insert("mensaje", {"id_conversacion": id_conversacion, "emisor": emisor, "texto": texto,
                                   "id_intencion": id_intencion}, returning="*")


def mensajes(id_conversacion):
    """Mensajes de la conversacion en orden cronologico.

    Args:
        id_conversacion (int): conversacion consultada.

    Returns:
        list[dict]: `emisor`, `texto`, `fecha`.
    """
    return repo.fetch_all("SELECT emisor, texto, fecha FROM mensaje WHERE id_conversacion = %s "
                          "ORDER BY id_mensaje", (id_conversacion,))


def ultima_intencion_asistente(id_conversacion):
    """Intencion del ultimo mensaje del asistente (sirve para escalar tras dos `no_entendido` seguidos).

    Args:
        id_conversacion (int): conversacion consultada.

    Returns:
        str | None: nombre de la intencion o `None` si el asistente aun no ha respondido.
    """
    r = repo.fetch_one(
        """SELECT i.nombre FROM mensaje m JOIN intencion i ON i.id_intencion = m.id_intencion
           WHERE m.id_conversacion = %s AND m.emisor = 'asistente' ORDER BY m.id_mensaje DESC LIMIT 1""",
        (id_conversacion,))
    return r["nombre"] if r else None


def va_con_bibliotecario(id_conversacion):
    """Indica si la conversacion fue pasada a un bibliotecario (algun mensaje con intencion `pasar_a_bibliotecario`, RF-33).

    Args:
        id_conversacion (int): conversacion consultada.

    Returns:
        bool: `True` si fue escalada.
    """
    return bool(repo.fetch_one(f"SELECT 1 AS x FROM conversacion c WHERE c.id_conversacion = %s AND {_CON_BIB}",
                               (id_conversacion,)))


def valorar(id_conversacion, valores):
    """Actualiza la opinion de la conversacion.

    Args:
        id_conversacion (int): conversacion a actualizar.
        valores (dict): columnas a modificar (`calificacion`, y opcionalmente `resuelta`, `fecha_fin`).

    Returns:
        dict: fila `conversacion` actualizada.
    """
    return repo.update("conversacion", "id_conversacion", id_conversacion, valores, returning="*")


def resolver(id_conversacion):
    """Marca la conversacion como resuelta y fija `fecha_fin` al momento actual.

    Args:
        id_conversacion (int): conversacion a cerrar.

    Returns:
        dict: fila `conversacion` actualizada.
    """
    return repo.update("conversacion", "id_conversacion", id_conversacion,
                       {"resuelta": True, "fecha_fin": datetime.now()}, returning="*")


def consultas_bibliotecario(estado=""):
    """Conversaciones escaladas a bibliotecario, pendientes primero y mas recientes primero (RF-33).

    Args:
        estado (str): `pendiente`, `resuelta`; cualquier otro valor (p. ej. `""`) no filtra.

    Returns:
        list[dict]: `id_conversacion`, `fecha_inicio`, `resuelta`, `calificacion`, `matricula` y `nombre_completo`
        (nulos si es visitante) y `ultimo_mensaje`.
    """
    resuelta = {"pendiente": False, "resuelta": True}.get(estado)
    rows = repo.fetch_all(
        f"""SELECT c.id_conversacion, c.fecha_inicio, c.resuelta, c.calificacion, u.matricula, u.nombre_completo,
                   (SELECT m.texto FROM mensaje m WHERE m.id_conversacion = c.id_conversacion
                    ORDER BY m.id_mensaje DESC LIMIT 1) AS ultimo_mensaje
            FROM conversacion c LEFT JOIN usuario u ON u.id_usuario = c.id_usuario
            WHERE {_CON_BIB} AND (%(r)s::boolean IS NULL OR c.resuelta = %(r)s)
            ORDER BY c.resuelta, c.fecha_inicio DESC, c.id_conversacion DESC""", {"r": resuelta})
    return rows
