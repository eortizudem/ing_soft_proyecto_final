"""Capa modelo del catálogo: acceso a datos SQL de libros, ejemplares y ubicaciones.

Solo consultas/escrituras (sin reglas de negocio; esas viven en `service.py`). La vista base calcula
existencias, prestados y disponibilidad en vivo (RF-14, RF-15).
"""

from psycopg import sql

from app.core import consultas, repo
from app.core.serializers import nest

_BASE = f"""
SELECT l.id_libro, l.clave, l.titulo, l.autor, l.editorial, l.tema, l.anio_publicacion, l.tipo_uso,
  l.clasificacion, l.sinopsis, l.precio_referencia, l.estado,
  u.planta, u.pasillo, u.librero, u.nivel,
  (SELECT count(*) FROM ejemplar e WHERE e.id_libro = l.id_libro AND e.estado <> 'baja')::int AS ejemplares,
  (SELECT count(*) FROM ejemplar e WHERE e.id_libro = l.id_libro AND e.estado = 'prestado')::int AS prestados,
  CASE WHEN l.estado = 'activo'
       THEN {consultas.disponibles('l')}
       ELSE 0 END AS disponibles
FROM libro l JOIN ubicacion u ON u.id_ubicacion = l.id_ubicacion
"""

_VISTA = f"SELECT * FROM ({_BASE}) v"  # permite filtrar por columnas calculadas
_COLS = ("clave", "titulo", "autor", "editorial", "tema", "anio_publicacion", "tipo_uso", "clasificacion",
         "sinopsis", "precio_referencia", "estado")


def _shape(r):
    """Anida las columnas de ubicación del renglón en `r['ubicacion']`.

    Args:
        r (dict): Renglón de la vista de libros.

    Returns:
        dict: El renglón con la clave `ubicacion` {planta, pasillo, librero, nivel}.
    """
    return nest(r, "ubicacion", ("planta", "pasillo", "librero", "nivel"))


# Busqueda por campo (RF-13..15): parametro -> columna de la vista.
CAMPOS = {"titulo": "v.titulo", "autor": "v.autor", "clave": "v.clave", "editorial": "v.editorial",
          "tema_texto": "v.tema", "clasificacion": "v.clasificacion"}


def list_(q="", tema="", estado="", solo_disponibles=False, campos=None, tipo_uso="", disponibilidad=""):
    """Lista libros con filtros (RF-12, RF-13, RF-15), ordenados por clave.

    Args:
        q (str): Texto libre; busca (sin acentos) en clave, título, autor, editorial, tema y clasificación.
        tema (str): Tema exacto; vacío = sin filtro.
        estado (str): 'activo' | 'inactivo'; vacío = ambos.
        solo_disponibles (bool): Si es True, solo libros con ejemplares disponibles (tiene prioridad sobre `disponibilidad`).
        campos (dict | None): {titulo|autor|clave|editorial|tema_texto|clasificacion: texto}; se combinan con AND, sin acentos.
        tipo_uso (str): 'prestamo_externo' | 'consulta_interna' | 'reservado'; vacío = sin filtro.
        disponibilidad (str): 'disponible' | 'agotado'; otro valor = sin filtro.

    Returns:
        list[dict]: Libros con ejemplares, prestados, disponibles y `ubicacion` anidada.
    """
    disp = {"disponible": {"v.disponibles__gt": 0}, "agotado": {"v.disponibles": 0}}.get(disponibilidad, {})
    if solo_disponibles:
        disp = {"v.disponibles__gt": 0}
    where, params = repo.build_where(
        {"v.tema": tema, "v.estado": estado, "v.tipo_uso": tipo_uso, **disp},
        search=(q, ["v.clave", "v.titulo", "v.autor", "v.editorial", "v.tema", "v.clasificacion"]))
    parts = [where]
    for campo, texto in (campos or {}).items():
        w, p = repo.build_where(search=(texto, [CAMPOS[campo]]))
        parts.append(w)
        params += p
    query = sql.SQL(_VISTA + " WHERE ") + sql.SQL(" AND ").join(parts) + sql.SQL(" ORDER BY v.clave")
    return [_shape(r) for r in repo.fetch_all(query, params)]


def get(id_libro):
    """Obtiene un libro por id con existencias, disponibilidad y ubicación.

    Args:
        id_libro (int): Id del libro.

    Returns:
        dict | None: El libro, o None si no existe.
    """
    return _shape(repo.fetch_one(_BASE + " WHERE l.id_libro = %s", (id_libro,)))


def clave_en_uso(clave, exclude_id=None):
    """Indica si la clave ya pertenece a otro libro.

    Args:
        clave (str): Clave a verificar.
        exclude_id (int | None): Id de libro a ignorar (al editar).

    Returns:
        bool: True si la clave está en uso.
    """
    return repo.exists("libro", {"clave": clave}, exclude=("id_libro", exclude_id))


def ubicacion_id(planta, pasillo, librero, nivel):
    """Devuelve el id de la ubicación (la crea si no existe) (RF-09).

    Args:
        planta (str): Planta.
        pasillo (str): Letra de pasillo.
        librero (str): Número de librero a dos dígitos.
        nivel (int): Nivel del librero.

    Returns:
        int: `id_ubicacion`.
    """
    return repo.get_or_create("ubicacion", {"planta": planta, "pasillo": pasillo, "librero": librero, "nivel": nivel},
                              "id_ubicacion")


def _row(d):
    """Convierte los datos validados a las columnas de la tabla `libro` (resuelve `id_ubicacion`).

    Args:
        d (dict): Datos validados con la clave `ubicacion` (tupla planta, pasillo, librero, nivel).

    Returns:
        dict: Columnas de `libro`.
    """
    return {**{c: d[c] for c in _COLS}, "id_ubicacion": ubicacion_id(*d["ubicacion"])}


def insert(d):
    """Inserta un libro (RF-08).

    Args:
        d (dict): Datos validados del libro.

    Returns:
        int: `id_libro` creado.
    """
    return repo.insert("libro", _row(d), returning="id_libro")["id_libro"]


def update(id_libro, d):
    """Actualiza los datos de ficha de un libro (no toca ejemplares).

    Args:
        id_libro (int): Id del libro.
        d (dict): Datos validados del libro.
    """
    repo.update("libro", "id_libro", id_libro, _row(d), returning=None)


def add_ejemplares(id_libro, n):
    """Crea `n` ejemplares nuevos con `numero_copia` consecutivo al máximo existente.

    También lo usa compras al recibir pedidos (RF-06).

    Args:
        id_libro (int): Id del libro.
        n (int): Cantidad de ejemplares a crear.
    """
    repo.execute(
        """INSERT INTO ejemplar(id_libro, numero_copia)
           SELECT %s, m.mx + g FROM generate_series(1, %s) g,
                  (SELECT COALESCE(max(numero_copia), 0) AS mx FROM ejemplar WHERE id_libro = %s) m""",
        (id_libro, n, id_libro))


def dar_baja_ejemplares(id_libro, n):
    """Marca como 'baja' (motivo 'obsoleto') hasta `n` ejemplares disponibles, de la copia mayor a la menor.

    Nunca toca los prestados (RF-11).

    Args:
        id_libro (int): Id del libro.
        n (int): Cantidad de ejemplares a dar de baja.
    """
    repo.execute(
        """UPDATE ejemplar SET estado='baja', motivo_baja='obsoleto' WHERE id_ejemplar IN (
             SELECT id_ejemplar FROM ejemplar WHERE id_libro=%s AND estado='disponible'
             ORDER BY numero_copia DESC LIMIT %s)""", (id_libro, n))


_EJEMPLAR = """
SELECT e.id_ejemplar, e.id_libro, l.clave, e.numero_copia, e.estado, e.motivo_baja, e.fecha_alta,
  p.id_prestamo, us.matricula, p.fecha_vencimiento,
  l.clave || '-' || lpad(e.numero_copia::text, 2, '0') AS etiqueta, l.estado AS estado_libro
FROM ejemplar e JOIN libro l ON l.id_libro = e.id_libro
LEFT JOIN prestamo p ON p.id_ejemplar = e.id_ejemplar AND p.fecha_devolucion IS NULL
LEFT JOIN usuario us ON us.id_usuario = p.id_usuario
"""


def _ejemplar(r):
    """Reestructura un renglón de ejemplar: agrupa el préstamo abierto en `prestamo_activo`.

    Args:
        r (dict | None): Renglón de `_EJEMPLAR`.

    Returns:
        dict | None: Ejemplar con `prestamo_activo` ({id_prestamo, matricula, fecha_vencimiento} o None); None si `r` es None.
    """
    if r is None:
        return None
    r = dict(r)
    activo = {"id_prestamo": r.pop("id_prestamo"), "matricula": r.pop("matricula"),
              "fecha_vencimiento": r.pop("fecha_vencimiento")}
    r["prestamo_activo"] = activo if activo["id_prestamo"] else None
    return r


def ejemplares(id_libro):
    """Lista los ejemplares de un libro (incluidas bajas) ordenados por copia (RF-11).

    Args:
        id_libro (int): Id del libro.

    Returns:
        list[dict]: Ejemplares con `etiqueta` (CLAVE-NN) y `prestamo_activo`.
    """
    return [_ejemplar(r) for r in repo.fetch_all(_EJEMPLAR + " WHERE e.id_libro = %s ORDER BY e.numero_copia", (id_libro,))]


def get_ejemplar(id_ejemplar):
    """Obtiene un ejemplar por id.

    Args:
        id_ejemplar (int): Id del ejemplar.

    Returns:
        dict | None: El ejemplar, o None si no existe.
    """
    return _ejemplar(repo.fetch_one(_EJEMPLAR + " WHERE e.id_ejemplar = %s", (id_ejemplar,)))


def baja_ejemplar(id_ejemplar, motivo):
    """Atómico: solo pasa a 'baja' si sigue 'disponible' (RF-11).

    Args:
        id_ejemplar (int): Id del ejemplar.
        motivo (str): Motivo de baja (perdido, robado, danado, obsoleto).

    Returns:
        bool: True si cambió de estado.
    """
    return repo.fetch_one("UPDATE ejemplar SET estado='baja', motivo_baja=%s WHERE id_ejemplar=%s AND estado='disponible' "
                          "RETURNING id_ejemplar", (motivo, id_ejemplar)) is not None


def reactivar_ejemplar(id_ejemplar):
    """Atómico: devuelve a 'disponible' un ejemplar que está en 'baja' (RF-11).

    Args:
        id_ejemplar (int): Id del ejemplar.

    Returns:
        bool: True si cambió de estado.
    """
    return repo.fetch_one("UPDATE ejemplar SET estado='disponible', motivo_baja=NULL WHERE id_ejemplar=%s AND estado='baja' "
                          "RETURNING id_ejemplar", (id_ejemplar,)) is not None


def etiquetas(id_libro):
    """Códigos de etiqueta de los ejemplares que no están de baja (RF-07).

    Args:
        id_libro (int): Id del libro.

    Returns:
        list[dict]: [{numero_copia, etiqueta}].
    """
    return [{"numero_copia": e["numero_copia"], "etiqueta": e["etiqueta"]}
            for e in ejemplares(id_libro) if e["estado"] != "baja"]


def pendientes():
    """Líneas de compra recibidas (cantidad_recibida > 0) aún sin libro del catálogo (RF-06).

    Excluye solicitudes canceladas.

    Returns:
        list[dict]: id_detalle, descripcion, cantidad_recibida, precio_unitario, folio.
    """
    return repo.fetch_all(
        """SELECT d.id_detalle, d.descripcion, d.cantidad_recibida, d.precio_unitario, s.folio
           FROM detalle_solicitud d JOIN solicitud_compra s ON s.id_solicitud = d.id_solicitud
           WHERE d.id_libro IS NULL AND d.cantidad_recibida > 0 AND s.estado <> 'cancelada'
           ORDER BY s.folio, d.id_detalle""")


def detalle(id_detalle):
    """Obtiene una línea de solicitud de compra.

    Args:
        id_detalle (int): Id de la línea.

    Returns:
        dict | None: {id_detalle, id_libro, cantidad_recibida} o None.
    """
    return repo.fetch_one("SELECT id_detalle, id_libro, cantidad_recibida FROM detalle_solicitud WHERE id_detalle = %s",
                          (id_detalle,))


def enlazar_detalle(id_detalle, id_libro):
    """Enlaza una línea de compra con el libro catalogado.

    Args:
        id_detalle (int): Id de la línea.
        id_libro (int): Id del libro.
    """
    repo.update("detalle_solicitud", "id_detalle", id_detalle, {"id_libro": id_libro}, returning=None)


def clave_existente(clave):
    """Busca un libro por clave.

    Args:
        clave (str): Clave del libro.

    Returns:
        dict | None: Resultado de `consultas.libro_por_clave`.
    """
    return consultas.libro_por_clave(clave)


def temas(solo_activos):
    """Temas distintos del catálogo, ordenados.

    Args:
        solo_activos (bool): Si es True, solo temas de libros activos.

    Returns:
        list[str]: Temas.
    """
    sql = "SELECT DISTINCT tema FROM libro" + (" WHERE estado='activo'" if solo_activos else "")
    return [r["tema"] for r in repo.fetch_all(sql + " ORDER BY tema")]
