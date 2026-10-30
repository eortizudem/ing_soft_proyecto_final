"""Modelo de la lista de espera: acceso a datos SQL (capa model del MVC).

Consultas y escrituras sobre `lista_espera` (FIFO por libro, estados activos en
`app.core.espera.ACTIVOS`). Sin reglas de negocio: viven en `service.py` y en
`app.core.circulacion`/`app.core.espera`.
"""
from app.core import consultas, repo
from app.core.espera import ACTIVOS
from app.core.serializers import nest


_BASE = f"""
SELECT le.id_espera, u.id_usuario, u.matricula, u.nombre_completo,
  l.id_libro, l.clave, l.titulo,
  {consultas.disponibles('l')} AS disponibles,
  le.posicion, le.estado, le.fecha_solicitud, le.fecha_notificacion, le.fecha_limite_recoger
FROM lista_espera le
JOIN usuario u ON u.id_usuario = le.id_usuario
JOIN libro l ON l.id_libro = le.id_libro
"""


def _shape(row):
    """Anida `usuario` y `libro` en una fila plana de `_BASE`.

    Args:
        row: Fila plana de `lista_espera` con usuario y libro.

    Returns:
        dict: Fila con `usuario` (id, matrícula, nombre) y `libro` (id, clave, título, disponibles).
    """
    row = nest(row, "usuario", ("id_usuario", "matricula", "nombre_completo"))
    return nest(row, "libro", ("id_libro", "clave", "titulo", "disponibles"))


def list_(estado="", id_libro=None, q="", id_usuario=None):
    """Lista entradas de espera ordenadas por título y posición.

    Args:
        estado: Filtro exacto por estado ('en_espera', 'notificado', ...); vacío = todos.
        id_libro: Filtro por libro; None/0 = todos.
        q: Texto libre sobre matrícula, nombre, clave y título.
        id_usuario: Filtro por usuario; None = todos.

    Returns:
        list[dict]: Entradas con `usuario` y `libro` anidados.
    """
    rows = repo.select(_BASE, {"le.estado": estado, "le.id_libro": id_libro, "le.id_usuario": id_usuario},
                       search=(q, ["u.matricula", "u.nombre_completo", "l.clave", "l.titulo"]),
                       order=["l.titulo", "le.posicion", "le.id_espera"])
    return [_shape(r) for r in rows]


def get(id_espera):
    """Obtiene una entrada de espera por id.

    Args:
        id_espera: Identificador de la entrada.

    Returns:
        dict: Entrada anidada. Nota: si no existe, `_shape` recibe None y falla; el service
        llama primero a `or_404`.
    """
    return _shape(repo.fetch_one(_BASE + " WHERE le.id_espera = %s", (id_espera,)))


def lock_libro(id_libro):
    """Serializa altas/avances de un mismo libro (posiciones consecutivas, sin duplicados concurrentes).

    Args:
        id_libro: Libro a bloquear con `FOR UPDATE`.

    Returns:
        dict | None: `id_libro`, o None si el libro no existe.
    """
    return repo.fetch_one("SELECT id_libro FROM libro WHERE id_libro = %s FOR UPDATE", (id_libro,))


def usuario(id_usuario):
    """Datos básicos de un usuario.

    Args:
        id_usuario: Identificador del usuario.

    Returns:
        dict | None: `id_usuario`, `matricula`, `nombre_completo` y `estado`, o None.
    """
    return repo.fetch_one("SELECT id_usuario, matricula, nombre_completo, estado FROM usuario WHERE id_usuario = %s",
                          (id_usuario,))


def tiene_prestamo(id_usuario, id_libro):
    """Indica si el usuario ya tiene un ejemplar de ese libro sin devolver.

    Args:
        id_usuario: Usuario a consultar.
        id_libro: Libro a consultar.

    Returns:
        bool: True si existe un préstamo abierto.
    """
    return repo.fetch_one(
        """SELECT 1 FROM prestamo p JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar
           WHERE p.id_usuario = %s AND e.id_libro = %s AND p.fecha_devolucion IS NULL LIMIT 1""",
        (id_usuario, id_libro)) is not None


def ya_en_espera(id_usuario, id_libro):
    """Indica si el usuario ya tiene una entrada activa para el libro.

    Args:
        id_usuario: Usuario a consultar.
        id_libro: Libro a consultar.

    Returns:
        bool: True si hay una entrada en estado activo.
    """
    return repo.fetch_one(
        "SELECT 1 FROM lista_espera WHERE id_usuario = %s AND id_libro = %s AND estado = ANY(%s) LIMIT 1",
        (id_usuario, id_libro, list(ACTIVOS))) is not None


def contar_activos(id_libro):
    """Cuenta las entradas activas de la fila de un libro.

    Args:
        id_libro: Libro a consultar.

    Returns:
        int: Número de entradas activas.
    """
    return repo.fetch_one("SELECT count(*)::int AS n FROM lista_espera WHERE id_libro = %s AND estado = ANY(%s)",
                          (id_libro, list(ACTIVOS)))["n"]


def insert(id_usuario, id_libro, posicion):
    """Inserta una entrada al final de la fila.

    Args:
        id_usuario: Usuario que se une.
        id_libro: Libro esperado.
        posicion: Posición asignada (activos + 1).

    Returns:
        int: `id_espera` generado.
    """
    return repo.insert("lista_espera", {"id_usuario": id_usuario, "id_libro": id_libro, "posicion": posicion},
                       returning="id_espera")["id_espera"]


def set_estado(id_espera, estado, **extra):
    """Cambia el estado de una entrada y, opcionalmente, otros campos.

    Args:
        id_espera: Entrada a actualizar.
        estado: Nuevo estado.
        **extra: Columnas adicionales (p. ej. `fecha_notificacion`).
    """
    repo.update("lista_espera", "id_espera", id_espera, {"estado": estado, **extra}, returning=None)


def renumerar(id_libro):
    """Posiciones consecutivas (1..n) de las entradas activas del libro, conservando el orden FIFO.

    Args:
        id_libro: Libro cuya fila se renumera.
    """
    repo.execute(
        """UPDATE lista_espera le SET posicion = n.rn
           FROM (SELECT id_espera, row_number() OVER (ORDER BY posicion, fecha_solicitud, id_espera)::int AS rn
                 FROM lista_espera WHERE id_libro = %s AND estado = ANY(%s)) n
           WHERE le.id_espera = n.id_espera AND le.posicion <> n.rn""",
        (id_libro, list(ACTIVOS)))


def vencidas():
    """Notificados cuyo plazo para recoger ya pasó (filas bloqueadas con `FOR UPDATE`).

    Returns:
        list[dict]: `id_espera`, `id_usuario` e `id_libro`.
    """
    return repo.fetch_all(
        """SELECT id_espera, id_usuario, id_libro FROM lista_espera
           WHERE estado = 'notificado' AND fecha_limite_recoger < now() ORDER BY id_espera FOR UPDATE""")


def libros_por_avanzar():
    """Libros cuya fila necesita mantenimiento: posiciones no consecutivas, o ejemplares disponibles sin apartar con
    alguien `en_espera` (misma definición de reservado que `core.circulacion.contexto_libro`).

    Returns:
        list[int]: Ids de libro.
    """
    return [r["id_libro"] for r in repo.fetch_all(
        """SELECT le.id_libro FROM lista_espera le WHERE le.estado = ANY(%s) GROUP BY le.id_libro
           HAVING min(le.posicion) <> 1 OR max(le.posicion) <> count(*)
              OR (count(*) FILTER (WHERE le.estado = 'en_espera') > 0
                  AND (SELECT count(*) FROM ejemplar e WHERE e.id_libro = le.id_libro AND e.estado = 'disponible')
                      > count(*) FILTER (WHERE le.estado = 'notificado'
                                         AND (le.fecha_limite_recoger IS NULL OR le.fecha_limite_recoger >= now())))
           ORDER BY le.id_libro""", (list(ACTIVOS),))]


def libros_opciones():
    """Libros activos de préstamo externo (candidatos a lista de espera) con su disponibilidad.

    Returns:
        list[dict]: `id_libro`, `clave`, `titulo`, `disponibles` y `en_espera`.
    """
    return repo.fetch_all(
        f"""SELECT l.id_libro, l.clave, l.titulo,
             {consultas.disponibles('l')} AS disponibles,
             (SELECT count(*) FROM lista_espera w WHERE w.id_libro = l.id_libro AND w.estado = ANY(%s))::int AS en_espera
           FROM libro l WHERE l.estado = 'activo' AND l.tipo_uso = 'prestamo_externo' ORDER BY l.titulo""",
        (list(ACTIVOS),))
