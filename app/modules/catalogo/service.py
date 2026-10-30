"""Capa servicio del catálogo: reglas de negocio de libros y ejemplares.

Validación de fichas (RF-08..RF-10), baja/reactivación de libros y ejemplares (RF-11), etiquetas (RF-07),
líneas de compra pendientes de catalogar (RF-06) e importación masiva CSV (PS-S1-12). Lanza `ApiError`.
"""

import csv
import io

from app.core.auth import has_permission
from app.core.bitacora import audit
from app.core.errors import ApiError
from app.core.estado import toggle_estado
from app.core.repo import or_404
from app.core.validators import CODE_RE, Enum, Int, Dec, Str, validate

from . import model

ESTADOS = ("activo", "inactivo")
TIPOS = ("prestamo_externo", "consulta_interna", "reservado")
MOTIVOS_BAJA = ("perdido", "robado", "danado", "obsoleto")
MAX_IMPORTAR = 1000
NO_ENCONTRADO = "No se encontró el libro."
CON_PRESTAMOS = "Libro con préstamos activos. Devuelve los ejemplares antes de darlo de baja."

SCHEMA = {
    "clave": Str("clave", upper=True, pattern=CODE_RE,
                 pattern_msg="La clave debe tener de 3 a 10 letras, números o guiones."),
    "titulo": Str("título", max=200),
    "autor": Str("autor", max=120),
    "editorial": Str("editorial", max=80),
    "tema": Str("tema", max=60),
    "clasificacion": Str("clasificación", max=20),
    "sinopsis": Str("sinopsis"),
    "ejemplares": Int(1, 10000, msg="El número de ejemplares debe ser un entero entre 1 y 10000."),
    "anio_publicacion": Int(1000, 2100, msg="Introduce un año entre 1000 y 2100."),
    "precio_referencia": Dec(0, 99999999, msg="El precio debe ser un número mayor o igual a cero."),
    "tipo_uso": Enum(TIPOS, "Selecciona un tipo de uso válido."),
    "id_detalle": Int(1, 2_000_000_000, required=False, msg="Línea de compra no válida."),
    "estado": Enum(ESTADOS, "Selecciona un estado válido.", required=False),
    "librero": Int(1, 12, msg="El librero debe ser un número entre 1 y 12."),
    "nivel": Int(1, 9, msg="El nivel debe ser un número entre 1 y 9."),
    "pasillo": Str("pasillo", upper=True, pattern=r"^[^\W_]$", pattern_msg="El pasillo debe ser una sola letra."),
    "planta": Str("planta", max=20),
}


def _ve_todo(user):
    """Indica si el usuario puede ver libros inactivos (permiso `catalogo`).

    Args:
        user (dict | None): Usuario en sesión.

    Returns:
        bool: True si tiene el permiso `catalogo`.
    """
    return has_permission(user, "catalogo")


def listar(user, q, tema, estado, solo_disponibles, campos=None, tipo_uso="", disponibilidad=""):
    """Lista libros según el rol (RF-12, RF-13, RF-15).

    Sin permiso `catalogo` solo se devuelven libros activos; filtros desconocidos o vacíos se ignoran.

    Args:
        user (dict | None): Usuario en sesión.
        q (str): Texto libre de búsqueda.
        tema (str): Tema exacto.
        estado (str): 'activo' | 'inactivo' (solo con permiso `catalogo`).
        solo_disponibles (bool): Solo con ejemplares disponibles.
        campos (dict | None): Búsqueda por campo (titulo, autor, clave, editorial, clasificacion).
        tipo_uso (str): Tipo de uso válido o vacío.
        disponibilidad (str): 'disponible' | 'agotado' o vacío.

    Returns:
        list[dict]: Libros.
    """
    if not _ve_todo(user):
        estado = "activo"
    elif estado not in ESTADOS:
        estado = ""
    campos = {k: v for k, v in (campos or {}).items() if k in model.CAMPOS and str(v).strip()}
    return model.list_(q, tema, estado, solo_disponibles, campos, tipo_uso if tipo_uso in TIPOS else "",
                       disponibilidad)


def obtener(user, id_libro):
    """Obtiene un libro; los inactivos solo son visibles con permiso `catalogo`.

    Args:
        user (dict | None): Usuario en sesión.
        id_libro (int): Id del libro.

    Returns:
        dict: El libro.

    Raises:
        ApiError: 404 si no existe o está inactivo y el usuario no tiene permiso.
    """
    libro = model.get(id_libro)
    if not libro or (libro["estado"] != "activo" and not _ve_todo(user)):
        raise ApiError(NO_ENCONTRADO, 404)
    return libro


def temas(user):
    """Temas disponibles (solo de libros activos si el usuario no tiene permiso `catalogo`).

    Args:
        user (dict | None): Usuario en sesión.

    Returns:
        list[str]: Temas.
    """
    return model.temas(not _ve_todo(user))


def _clean(d, old):
    """Valida la ficha del libro y las reglas de unicidad y enlace con compras.

    Args:
        d (dict): Payload crudo.
        old (dict | None): Libro actual al editar; None al crear.

    Returns:
        dict: Datos validados con `estado` resuelto y `ubicacion` (planta, pasillo, librero a 2 dígitos, nivel).

    Raises:
        ApiError: 400 con mensaje de campo si falla el esquema; 400 si la clave ya existe;
            404 si la línea de compra no existe; 409 si la línea ya está enlazada a otro libro.
    """
    data = validate(d, SCHEMA)
    if model.clave_en_uso(data["clave"], old["id_libro"] if old else None):
        raise ApiError("Ya existe un libro con esa clave.")
    data["estado"] = data["estado"] or (old["estado"] if old else "activo")
    if data.get("id_detalle"):
        d = or_404(model.detalle(data["id_detalle"]), "No se encontró la línea de compra.")
        if d["id_libro"] and (not old or d["id_libro"] != old["id_libro"]):
            raise ApiError("La línea de compra ya está enlazada a un libro.", 409)
    data["ubicacion"] = (data["planta"], data["pasillo"], f"{data['librero']:02d}", data["nivel"])
    return data


@audit("libro_crear", lambda b: f"Alta de {b['clave']} - {b['titulo']}")
def crear(d, actor):
    """Alta de libro con sus ejemplares y ubicación (RF-08, RF-09, RF-10); opcionalmente enlaza una línea de compra.

    Bitácora: `libro_crear`.

    Args:
        d (dict): Payload (clave, titulo, autor, editorial, tema, clasificacion, sinopsis, ejemplares, anio_publicacion,
            precio_referencia, tipo_uso, planta, pasillo, librero, nivel, id_detalle opcional).
        actor (dict): Usuario que realiza la acción.

    Returns:
        dict: Libro creado.

    Raises:
        ApiError: Ver `_clean`.
    """
    data = _clean(d, None)
    id_libro = model.insert(data)
    model.add_ejemplares(id_libro, data["ejemplares"])
    if data.get("id_detalle"):
        model.enlazar_detalle(data["id_detalle"], id_libro)
    return model.get(id_libro)


@audit("libro_editar", lambda b: f"Edición de {b['clave']}")
def actualizar(id_libro, d, actor):
    """Edita la ficha del libro y ajusta el número de ejemplares (RF-08, RF-11).

    Si aumenta `ejemplares` crea copias; si disminuye da de baja copias disponibles. Bitácora: `libro_editar`.

    Args:
        id_libro (int): Id del libro.
        d (dict): Payload completo (ver `crear`).
        actor (dict): Usuario que realiza la acción.

    Returns:
        dict: Libro actualizado.

    Raises:
        ApiError: 404 si no existe; 400 si `ejemplares` es menor que los prestados, si se inactiva con préstamos
            activos o por errores de `_clean`.
    """
    old = or_404(model.get(id_libro), NO_ENCONTRADO)
    data = _clean(d, old)
    n, prestados = data["ejemplares"], old["prestados"]
    if n < prestados:
        raise ApiError("No puedes registrar menos copias que las actualmente prestadas.")
    if data["estado"] == "inactivo" and old["estado"] == "activo" and prestados > 0:
        raise ApiError(CON_PRESTAMOS)
    model.update(id_libro, data)
    if data.get("id_detalle"):
        model.enlazar_detalle(data["id_detalle"], id_libro)
    actuales = old["ejemplares"]
    if n > actuales:
        model.add_ejemplares(id_libro, n - actuales)
    elif n < actuales:
        model.dar_baja_ejemplares(id_libro, actuales - n)
    return model.get(id_libro)


def _guard_baja(libro, nuevo):
    """Impide inactivar un libro con préstamos activos.

    Args:
        libro (dict): Libro actual.
        nuevo (str): Estado destino.

    Raises:
        ApiError: 400 si `nuevo` es 'inactivo' y hay ejemplares prestados.
    """
    if nuevo == "inactivo" and libro["prestados"] > 0:
        raise ApiError(CON_PRESTAMOS)


@audit(lambda b: "libro_baja" if b["estado"] == "inactivo" else "libro_reactivar",
       lambda b: f"{'Baja' if b['estado'] == 'inactivo' else 'Reactivación'} de {b['clave']}")
def alternar(id_libro, actor):
    """Activa o inactiva un libro (RF-11). Bitácora: `libro_baja` o `libro_reactivar`.

    Args:
        id_libro (int): Id del libro.
        actor (dict): Usuario que realiza la acción.

    Returns:
        dict: Libro con el estado actualizado.

    Raises:
        ApiError: 404 si no existe; 400 si se inactiva con préstamos activos.
    """
    toggle_estado("libro", "id_libro", id_libro, guard=_guard_baja,
                  load=lambda i: or_404(model.get(i), NO_ENCONTRADO))
    return model.get(id_libro)


# ---- Ejemplares (RF-11), etiqueta (RF-07), pendientes de catalogar, importación (PS-S1-12) ----

def _libro_o_404(id_libro):
    """Obtiene el libro o lanza 404.

    Args:
        id_libro (int): Id del libro.

    Returns:
        dict: El libro.

    Raises:
        ApiError: 404 si no existe.
    """
    return or_404(model.get(id_libro), NO_ENCONTRADO)


def ejemplares(id_libro):
    """Lista los ejemplares de un libro (RF-11).

    Args:
        id_libro (int): Id del libro.

    Returns:
        list[dict]: Ejemplares con etiqueta y préstamo activo.

    Raises:
        ApiError: 404 si el libro no existe.
    """
    _libro_o_404(id_libro)
    return model.ejemplares(id_libro)


def _ejemplar_o_404(id_ejemplar):
    """Obtiene el ejemplar o lanza 404.

    Args:
        id_ejemplar (int): Id del ejemplar.

    Returns:
        dict: El ejemplar.

    Raises:
        ApiError: 404 si no existe.
    """
    return or_404(model.get_ejemplar(id_ejemplar), "No se encontró el ejemplar.")


BAJA_SCHEMA = {
    "motivo": Enum(MOTIVOS_BAJA, "Selecciona un motivo de baja válido (perdido, robado, dañado u obsoleto)."),
    "observacion": Str("observación", max=120, required=False),
}


@audit("ejemplar_baja", lambda r, a: f"Baja de {r['etiqueta']} ({r['motivo_baja']})"
       + (f": {a['d'].get('observacion')}" if isinstance(a["d"], dict) and a["d"].get("observacion") else ""))
def baja_ejemplar(id_ejemplar, d, actor):
    """Da de baja un ejemplar disponible con motivo (RF-11). Bitácora: `ejemplar_baja`.

    Un ejemplar prestado no se puede dar de baja aquí: la pérdida se registra en Multas y pagos.

    Args:
        id_ejemplar (int): Id del ejemplar.
        d (dict): Payload {motivo: perdido|robado|danado|obsoleto, observacion opcional (máx. 120)}.
        actor (dict): Usuario que realiza la acción.

    Returns:
        dict: Ejemplar actualizado.

    Raises:
        ApiError: 400 por motivo inválido; 404 si no existe; 409 si está prestado, ya está de baja
            o cambió de estado concurrentemente.
    """
    data = validate(d, BAJA_SCHEMA)
    ej = _ejemplar_o_404(id_ejemplar)
    if ej["estado"] == "prestado":
        raise ApiError("El ejemplar está prestado: usa Multas y pagos para registrar la pérdida.", 409)
    if ej["estado"] == "baja":
        raise ApiError("El ejemplar ya está dado de baja.", 409)
    if not model.baja_ejemplar(id_ejemplar, data["motivo"]):
        raise ApiError("El ejemplar cambió de estado. Actualiza e inténtalo de nuevo.", 409)
    return model.get_ejemplar(id_ejemplar)


@audit("ejemplar_reactivar", lambda r: f"Reactivación de {r['etiqueta']}")
def reactivar_ejemplar(id_ejemplar, actor):
    """Reactiva un ejemplar dado de baja (RF-11). Bitácora: `ejemplar_reactivar`.

    Args:
        id_ejemplar (int): Id del ejemplar.
        actor (dict): Usuario que realiza la acción.

    Returns:
        dict: Ejemplar reactivado.

    Raises:
        ApiError: 404 si no existe; 409 si no está de baja o si el libro está inactivo.
    """
    ej = _ejemplar_o_404(id_ejemplar)
    if ej["estado"] != "baja":
        raise ApiError("Solo se pueden reactivar ejemplares dados de baja.", 409)
    if ej["estado_libro"] != "activo":
        raise ApiError("El libro está dado de baja: reactívalo antes de reactivar sus ejemplares.", 409)
    model.reactivar_ejemplar(id_ejemplar)
    return model.get_ejemplar(id_ejemplar)


def etiqueta(id_libro):
    """Datos de la ficha/etiqueta de un libro para imprimir (RF-07).

    Args:
        id_libro (int): Id del libro.

    Returns:
        dict: {clave, titulo, autor, clasificacion, ubicacion, codigo_ejemplares}.

    Raises:
        ApiError: 404 si el libro no existe.
    """
    b = _libro_o_404(id_libro)
    return {"clave": b["clave"], "titulo": b["titulo"], "autor": b["autor"], "clasificacion": b["clasificacion"],
            "ubicacion": b["ubicacion"], "codigo_ejemplares": model.etiquetas(id_libro)}


def pendientes():
    """Líneas de compra recibidas que aún no tienen libro en el catálogo (RF-06).

    Returns:
        list[dict]: Líneas pendientes de catalogar.
    """
    return model.pendientes()


_DEFAULTS = {"tipo_uso": "prestamo_externo", "planta": "Planta baja", "pasillo": "A", "librero": "1", "nivel": "1",
             "ejemplares": "1"}


def importar(d, actor):
    """Alta masiva desde CSV (PS-S1-12; cabecera obligatoria: columnas del esquema).

    Crea las filas válidas (con valores por defecto para tipo_uso, ubicación y ejemplares) e informa los errores por línea.

    Args:
        d (dict): Payload {csv: texto}; máximo `MAX_IMPORTAR` filas.
        actor (dict): Usuario que realiza la acción.

    Returns:
        dict: {creados: int, errores: [{linea, motivo}]}.

    Raises:
        ApiError: 400 si el CSV está vacío o excede `MAX_IMPORTAR` filas.
    """
    texto = (d.get("csv") if isinstance(d, dict) else None) or ""
    if not isinstance(texto, str) or not texto.strip():
        raise ApiError("Pega o carga el contenido CSV.")
    filas = list(csv.DictReader(io.StringIO(texto.lstrip("\ufeff"))))
    if len(filas) > MAX_IMPORTAR:
        raise ApiError(f"El archivo admite máximo {MAX_IMPORTAR} filas.")
    creados, errores = 0, []
    for n, fila in enumerate(filas, start=2):  # la línea 1 es la cabecera
        fila = {(k or "").strip(): (v or "").strip() for k, v in fila.items() if k}
        fila = {**_DEFAULTS, **{k: v for k, v in fila.items() if v != ""}}
        fila.pop("id_detalle", None)
        try:
            crear(fila, actor)
            creados += 1
        except ApiError as e:
            errores.append({"linea": n, "motivo": e.message})
    return {"creados": creados, "errores": errores}
