import psycopg

from app.core import circulacion, consultas, espera
from app.core.auth import has_permission
from app.core.bitacora import audit, log
from app.core.errors import ApiError, exigir, motivo
from app.core.repo import or_404
from app.core.validators import Int, Str, validate

from . import model

NO_ENCONTRADA = "No se encontró la solicitud de espera."
HAY_DISPONIBLES = "HAY_DISPONIBLES"
YA_EN_ESPERA = "YA_EN_ESPERA"
YA_TIENE_PRESTAMO = "YA_TIENE_PRESTAMO"

_LIBRO = Int(1, 2147483647, msg="Selecciona un libro válido.")
SCHEMA_ALTA = {"matricula": Str("matrícula / nómina", upper=True, max=24), "id_libro": _LIBRO}
SCHEMA_UNIRSE = {"id_libro": _LIBRO}


def barrer():
    """Mantenimiento perezoso: expira reservados vencidos (-> cancelado), renumera y avanza la fila.
    Solo toca los libros que lo necesitan (con 1,000 entradas esperando, barrerlos todos en cada GET costaba ~1.7 s)."""
    tocados = set(model.libros_por_avanzar())
    for v in model.vencidas():
        model.set_estado(v["id_espera"], "cancelado")
        log(v["id_usuario"], "espera_expirar", f"Venció el plazo para recoger (espera {v['id_espera']})")
        tocados.add(v["id_libro"])
    for id_libro in sorted(tocados):
        model.lock_libro(id_libro)
        model.renumerar(id_libro)
        espera.notificar_espera(id_libro)


def listar(estado, id_libro, q):
    barrer()
    return model.list_(estado, id_libro or None, q)


def mias(actor):
    _exigir_usuario(actor)
    barrer()
    return sorted(model.list_(id_usuario=actor["id_usuario"]), key=lambda e: -e["id_espera"])


def libros():
    return model.libros_opciones()


def _exigir_usuario(actor):
    if not actor.get("id_usuario"):
        raise ApiError("Inicia sesión con tu cuenta para usar la lista de espera.", 403)


def _unir(usuario, id_libro):
    or_404(model.lock_libro(id_libro), "No se encontró el libro.")
    ctx = circulacion.contexto_libro(id_libro)
    lib = ctx["libro"]
    motivos = []
    if usuario["estado"] != "activo":
        motivos.append(motivo(circulacion.USUARIO_INACTIVO, "El usuario está inactivo."))
    if lib["estado"] != "activo" or lib["tipo_uso"] != "prestamo_externo":
        motivos.append(motivo(circulacion.LIBRO_NO_PRESTABLE, "El libro no es de préstamo externo o está inactivo."))
    elif ctx["disponibles"] > ctx["reservados"]:
        motivos.append(motivo(HAY_DISPONIBLES, "Hay ejemplares disponibles: solicita el préstamo directamente."))
    if model.ya_en_espera(usuario["id_usuario"], id_libro):
        motivos.append(motivo(YA_EN_ESPERA, "El usuario ya está en la lista de espera de este libro."))
    if model.tiene_prestamo(usuario["id_usuario"], id_libro):
        motivos.append(motivo(YA_TIENE_PRESTAMO, "El usuario ya tiene un ejemplar de este libro en préstamo."))
    exigir(motivos, "No se puede añadir a la lista de espera.")
    try:
        nuevo = model.insert(usuario["id_usuario"], id_libro, model.contar_activos(id_libro) + 1)
    except psycopg.errors.UniqueViolation:
        raise ApiError.reglas([motivo(YA_EN_ESPERA, "El usuario ya está en la lista de espera de este libro.")],
                              "No se puede añadir a la lista de espera.")
    return model.get(nuevo)


@audit("espera_alta", lambda e: f"{e['usuario']['matricula']} en espera de {e['libro']['clave']} (pos. {e['posicion']})")
def crear(d, actor):
    data = validate(d, SCHEMA_ALTA)
    usuario = or_404(consultas.usuario_por_matricula(data["matricula"]), "No se encontró el usuario.")
    return _unir(usuario, data["id_libro"])


@audit("espera_alta", lambda e: f"{e['usuario']['matricula']} en espera de {e['libro']['clave']} (pos. {e['posicion']})")
def unirse(d, actor):
    _exigir_usuario(actor)
    data = validate(d, SCHEMA_UNIRSE)
    return _unir(model.usuario(actor["id_usuario"]), data["id_libro"])


@audit("espera_cancelar", lambda e: f"Cancelada espera de {e['usuario']['matricula']} en {e['libro']['clave']}")
def cancelar(id_espera, actor):
    entrada = or_404(model.get(id_espera), NO_ENCONTRADA)
    if not has_permission(actor, "espera") and entrada["usuario"]["id_usuario"] != actor.get("id_usuario"):
        raise ApiError("No tienes permiso para realizar esta acción.", 403)
    if entrada["estado"] not in model.ACTIVOS:
        raise ApiError("La solicitud ya no está activa.", 409)
    id_libro = entrada["libro"]["id_libro"]
    model.lock_libro(id_libro)
    model.set_estado(id_espera, "cancelado")
    model.renumerar(id_libro)
    if entrada["estado"] == "notificado":  # el ejemplar reservado queda libre para el siguiente
        espera.notificar_espera(id_libro)
    return model.get(id_espera)
