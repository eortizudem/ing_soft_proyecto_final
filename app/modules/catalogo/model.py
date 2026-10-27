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
    return nest(r, "ubicacion", ("planta", "pasillo", "librero", "nivel"))


# Busqueda por campo (RF-13..15): parametro -> columna de la vista.
CAMPOS = {"titulo": "v.titulo", "autor": "v.autor", "clave": "v.clave", "editorial": "v.editorial",
          "tema_texto": "v.tema", "clasificacion": "v.clasificacion"}


def list_(q="", tema="", estado="", solo_disponibles=False, campos=None, tipo_uso="", disponibilidad=""):
    """Lista libros. `campos`: {titulo|autor|clave|editorial|tema_texto|clasificacion: texto} (AND, sin acentos)."""
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
    return _shape(repo.fetch_one(_BASE + " WHERE l.id_libro = %s", (id_libro,)))


def clave_en_uso(clave, exclude_id=None):
    return repo.exists("libro", {"clave": clave}, exclude=("id_libro", exclude_id))


def ubicacion_id(planta, pasillo, librero, nivel):
    return repo.get_or_create("ubicacion", {"planta": planta, "pasillo": pasillo, "librero": librero, "nivel": nivel},
                              "id_ubicacion")


def _row(d):
    return {**{c: d[c] for c in _COLS}, "id_ubicacion": ubicacion_id(*d["ubicacion"])}


def insert(d):
    return repo.insert("libro", _row(d), returning="id_libro")["id_libro"]


def update(id_libro, d):
    repo.update("libro", "id_libro", id_libro, _row(d), returning=None)


def add_ejemplares(id_libro, n):
    repo.execute(
        """INSERT INTO ejemplar(id_libro, numero_copia)
           SELECT %s, m.mx + g FROM generate_series(1, %s) g,
                  (SELECT COALESCE(max(numero_copia), 0) AS mx FROM ejemplar WHERE id_libro = %s) m""",
        (id_libro, n, id_libro))


def dar_baja_ejemplares(id_libro, n):
    """Marca como 'baja' n ejemplares disponibles (nunca toca los prestados)."""
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
    if r is None:
        return None
    r = dict(r)
    activo = {"id_prestamo": r.pop("id_prestamo"), "matricula": r.pop("matricula"),
              "fecha_vencimiento": r.pop("fecha_vencimiento")}
    r["prestamo_activo"] = activo if activo["id_prestamo"] else None
    return r


def ejemplares(id_libro):
    return [_ejemplar(r) for r in repo.fetch_all(_EJEMPLAR + " WHERE e.id_libro = %s ORDER BY e.numero_copia", (id_libro,))]


def get_ejemplar(id_ejemplar):
    return _ejemplar(repo.fetch_one(_EJEMPLAR + " WHERE e.id_ejemplar = %s", (id_ejemplar,)))


def baja_ejemplar(id_ejemplar, motivo):
    """Atomico: solo pasa a 'baja' si sigue 'disponible'. Devuelve True si cambio."""
    return repo.fetch_one("UPDATE ejemplar SET estado='baja', motivo_baja=%s WHERE id_ejemplar=%s AND estado='disponible' "
                          "RETURNING id_ejemplar", (motivo, id_ejemplar)) is not None


def reactivar_ejemplar(id_ejemplar):
    return repo.fetch_one("UPDATE ejemplar SET estado='disponible', motivo_baja=NULL WHERE id_ejemplar=%s AND estado='baja' "
                          "RETURNING id_ejemplar", (id_ejemplar,)) is not None


def etiquetas(id_libro):
    return [{"numero_copia": e["numero_copia"], "etiqueta": e["etiqueta"]}
            for e in ejemplares(id_libro) if e["estado"] != "baja"]


def pendientes():
    """Lineas de compra recibidas (cantidad_recibida > 0) aun sin libro del catalogo."""
    return repo.fetch_all(
        """SELECT d.id_detalle, d.descripcion, d.cantidad_recibida, d.precio_unitario, s.folio
           FROM detalle_solicitud d JOIN solicitud_compra s ON s.id_solicitud = d.id_solicitud
           WHERE d.id_libro IS NULL AND d.cantidad_recibida > 0 AND s.estado <> 'cancelada'
           ORDER BY s.folio, d.id_detalle""")


def detalle(id_detalle):
    return repo.fetch_one("SELECT id_detalle, id_libro, cantidad_recibida FROM detalle_solicitud WHERE id_detalle = %s",
                          (id_detalle,))


def enlazar_detalle(id_detalle, id_libro):
    repo.update("detalle_solicitud", "id_detalle", id_detalle, {"id_libro": id_libro}, returning=None)


def clave_existente(clave):
    return consultas.libro_por_clave(clave)


def temas(solo_activos):
    sql = "SELECT DISTINCT tema FROM libro" + (" WHERE estado='activo'" if solo_activos else "")
    return [r["tema"] for r in repo.fetch_all(sql + " ORDER BY tema")]
