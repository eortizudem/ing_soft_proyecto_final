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
    return has_permission(user, "catalogo")


def listar(user, q, tema, estado, solo_disponibles, campos=None, tipo_uso="", disponibilidad=""):
    if not _ve_todo(user):
        estado = "activo"
    elif estado not in ESTADOS:
        estado = ""
    campos = {k: v for k, v in (campos or {}).items() if k in model.CAMPOS and str(v).strip()}
    return model.list_(q, tema, estado, solo_disponibles, campos, tipo_uso if tipo_uso in TIPOS else "",
                       disponibilidad)


def obtener(user, id_libro):
    libro = model.get(id_libro)
    if not libro or (libro["estado"] != "activo" and not _ve_todo(user)):
        raise ApiError(NO_ENCONTRADO, 404)
    return libro


def temas(user):
    return model.temas(not _ve_todo(user))


def _clean(d, old):
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
    data = _clean(d, None)
    id_libro = model.insert(data)
    model.add_ejemplares(id_libro, data["ejemplares"])
    if data.get("id_detalle"):
        model.enlazar_detalle(data["id_detalle"], id_libro)
    return model.get(id_libro)


@audit("libro_editar", lambda b: f"Edición de {b['clave']}")
def actualizar(id_libro, d, actor):
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
    if nuevo == "inactivo" and libro["prestados"] > 0:
        raise ApiError(CON_PRESTAMOS)


@audit(lambda b: "libro_baja" if b["estado"] == "inactivo" else "libro_reactivar",
       lambda b: f"{'Baja' if b['estado'] == 'inactivo' else 'Reactivación'} de {b['clave']}")
def alternar(id_libro, actor):
    toggle_estado("libro", "id_libro", id_libro, guard=_guard_baja,
                  load=lambda i: or_404(model.get(i), NO_ENCONTRADO))
    return model.get(id_libro)


# ---- Ejemplares (RF-11), etiqueta (RF-07), pendientes de catalogar, importación (PS-S1-12) ----

def _libro_o_404(id_libro):
    return or_404(model.get(id_libro), NO_ENCONTRADO)


def ejemplares(id_libro):
    _libro_o_404(id_libro)
    return model.ejemplares(id_libro)


def _ejemplar_o_404(id_ejemplar):
    return or_404(model.get_ejemplar(id_ejemplar), "No se encontró el ejemplar.")


BAJA_SCHEMA = {
    "motivo": Enum(MOTIVOS_BAJA, "Selecciona un motivo de baja válido (perdido, robado, dañado u obsoleto)."),
    "observacion": Str("observación", max=120, required=False),
}


@audit("ejemplar_baja", lambda r, a: f"Baja de {r['etiqueta']} ({r['motivo_baja']})"
       + (f": {a['d'].get('observacion')}" if isinstance(a["d"], dict) and a["d"].get("observacion") else ""))
def baja_ejemplar(id_ejemplar, d, actor):
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
    ej = _ejemplar_o_404(id_ejemplar)
    if ej["estado"] != "baja":
        raise ApiError("Solo se pueden reactivar ejemplares dados de baja.", 409)
    if ej["estado_libro"] != "activo":
        raise ApiError("El libro está dado de baja: reactívalo antes de reactivar sus ejemplares.", 409)
    model.reactivar_ejemplar(id_ejemplar)
    return model.get_ejemplar(id_ejemplar)


def etiqueta(id_libro):
    b = _libro_o_404(id_libro)
    return {"clave": b["clave"], "titulo": b["titulo"], "autor": b["autor"], "clasificacion": b["clasificacion"],
            "ubicacion": b["ubicacion"], "codigo_ejemplares": model.etiquetas(id_libro)}


def pendientes():
    return model.pendientes()


_DEFAULTS = {"tipo_uso": "prestamo_externo", "planta": "Planta baja", "pasillo": "A", "librero": "1", "nivel": "1",
             "ejemplares": "1"}


def importar(d, actor):
    """Alta masiva desde CSV (cabecera obligatoria: columnas del esquema). Crea las filas válidas e informa errores."""
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
