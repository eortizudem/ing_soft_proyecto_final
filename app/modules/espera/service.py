"""Servicio de la lista de espera: reglas de negocio (capa service del MVC).

FIFO por libro (D-19, RF-22): alta por personal o autoservicio, cancelación y
mantenimiento perezoso (`barrer`) que expira plazos vencidos, renumera y notifica al
siguiente. Errores con `ApiError` (400 validación, 403 permiso, 404, 409, 422 con `motivos`).
"""
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

    Solo toca los libros que lo necesitan (con 1,000 entradas esperando, barrerlos todos en cada GET costaba ~1.7 s).
    Registra `espera_expirar` en bitácora por cada plazo vencido.
    """
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
    """Lista la lista de espera (personal, RF-22) tras ejecutar `barrer`.

    Args:
        estado: Filtro por estado o vacío.
        id_libro: Filtro por libro (0/None = todos).
        q: Texto libre.

    Returns:
        list[dict]: Entradas con `usuario` y `libro` anidados.
    """
    barrer()
    return model.list_(estado, id_libro or None, q)


def mias(actor):
    """Solicitudes de espera del usuario autenticado, más recientes primero.

    Args:
        actor: Usuario autenticado.

    Returns:
        list[dict]: Entradas del propio usuario.

    Raises:
        ApiError: 403 si la sesión no corresponde a una cuenta de usuario.
    """
    _exigir_usuario(actor)
    barrer()
    return sorted(model.list_(id_usuario=actor["id_usuario"]), key=lambda e: -e["id_espera"])


def libros():
    """Libros candidatos a lista de espera con disponibilidad.

    Returns:
        list[dict]: Ver `model.libros_opciones`.
    """
    return model.libros_opciones()


def _exigir_usuario(actor):
    """Exige que el actor sea una cuenta de usuario con `id_usuario`.

    Args:
        actor: Usuario autenticado.

    Raises:
        ApiError: 403 si no tiene `id_usuario`.
    """
    if not actor.get("id_usuario"):
        raise ApiError("Inicia sesión con tu cuenta para usar la lista de espera.", 403)


def _unir(usuario, id_libro):
    """Añade a un usuario al final de la fila de un libro (D-19).

    Bloquea el libro y valida: usuario activo, libro activo de préstamo externo, sin ejemplares
    disponibles libres, no duplicado y sin préstamo abierto del mismo libro.

    Args:
        usuario: Fila del usuario (con `estado`).
        id_libro: Libro solicitado.

    Returns:
        dict: Entrada creada.

    Raises:
        ApiError: 404 si el libro no existe; 422 con `motivos` (USUARIO_INACTIVO,
        LIBRO_NO_PRESTABLE, HAY_DISPONIBLES, YA_EN_ESPERA, YA_TIENE_PRESTAMO).
    """
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
    """Alta en la lista de espera por el personal, indicando la matrícula (RF-22).

    Args:
        d: JSON con `matricula` e `id_libro`.
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: Entrada creada.

    Raises:
        ApiError: 400 payload inválido; 404 usuario o libro inexistente; 422 con `motivos` (ver `_unir`).
    """
    data = validate(d, SCHEMA_ALTA)
    usuario = or_404(consultas.usuario_por_matricula(data["matricula"]), "No se encontró el usuario.")
    return _unir(usuario, data["id_libro"])


@audit("espera_alta", lambda e: f"{e['usuario']['matricula']} en espera de {e['libro']['clave']} (pos. {e['posicion']})")
def unirse(d, actor):
    """Autoservicio: el usuario autenticado se une a la lista de espera de un libro.

    Args:
        d: JSON con `id_libro`.
        actor: Usuario autenticado.

    Returns:
        dict: Entrada creada.

    Raises:
        ApiError: 403 sin cuenta de usuario; 400 payload inválido; 404 libro; 422 con `motivos` (ver `_unir`).
    """
    _exigir_usuario(actor)
    data = validate(d, SCHEMA_UNIRSE)
    return _unir(model.usuario(actor["id_usuario"]), data["id_libro"])


@audit("espera_cancelar", lambda e: f"Cancelada espera de {e['usuario']['matricula']} en {e['libro']['clave']}")
def cancelar(id_espera, actor):
    """Cancela una entrada activa y renumera la fila; si estaba notificada avanza al siguiente.

    Permite cancelar al personal con permiso `espera` o al propio dueño de la entrada.

    Args:
        id_espera: Entrada a cancelar.
        actor: Usuario autenticado.

    Returns:
        dict: Entrada ya cancelada.

    Raises:
        ApiError: 404 no existe; 403 sin permiso ni ser el dueño; 409 si ya no está activa.
    """
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
