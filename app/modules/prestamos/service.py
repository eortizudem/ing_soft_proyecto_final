"""Servicio de préstamos: reglas de negocio (capa service del MVC).

Orquesta validación, préstamo, renovación, devolución, recibo y políticas.
Toda decisión de circulación sale de `app.core.circulacion` (RN-01..RN-06); aquí se
coordinan transacciones, bloqueos, bitácora (`@audit`) y notificaciones. Los errores se
reportan con `ApiError` (400 validación, 404 no encontrado, 409 conflicto, 422 reglas
con `motivos`).
"""
from datetime import date

from app.core import circulacion, consultas, espera, notificaciones
from app.core.auth import require_permission
from app.core.bitacora import audit
from app.core.errors import ApiError, exigir, motivo
from app.core.repo import or_404
from app.core.serializers import nest
from app.core.validators import Dec, Int, List, Str, validate

from . import model

USUARIO_NO_ENCONTRADO = "USUARIO_NO_ENCONTRADO"
LIBRO_NO_ENCONTRADO = "LIBRO_NO_ENCONTRADO"
CANALES_RECIBO = ("email", "whatsapp")
NO_ENCONTRADO = "No se encontró el préstamo."

SCHEMA_VALIDAR = {
    "matricula": Str("matrícula", upper=True, max=24),
    "clave": Str("clave", required=False, default="", upper=True, max=24),
    "id_libro": Int(1, label="libro", required=False, msg="Libro no válido."),
}
SCHEMA_CREAR = {**SCHEMA_VALIDAR, "canales": List(Str("canal"), required=False, msg="Canales no válidos.")}
SCHEMA_ENVIAR = {"canales": List(Str("canal"), min=1, msg="Selecciona al menos un canal.")}
SCHEMA_POLITICA = {
    "dias_prestamo": Int(1, 365, msg="Los días de préstamo deben ser un entero entre 1 y 365."),
    "max_libros": Int(1, 100, msg="El máximo de libros debe ser un entero entre 1 y 100."),
    "max_renovaciones": Int(1, 20, msg="El máximo de renovaciones debe ser un entero entre 1 y 20."),
    "multa_diaria": Dec(0, 99999, places=2, msg="La multa diaria debe ser un importe mayor o igual a 0."),
}


# ----------------------------------------------------------------- formato
def _shape(row):
    """Convierte una fila plana en el contrato de la API.

    Anida `usuario` y `libro`, añade `dias_retraso` y `multa_estimada` (no persistida, D-24/D-04)
    y retira `multa_diaria`.

    Args:
        row: Fila plana de `model.get`/`model.list_`.

    Returns:
        dict: Préstamo con `usuario`, `libro`, `dias_retraso` y `multa_estimada`.
    """
    hasta = row["fecha_devolucion"] or date.today()
    dias = circulacion.dias_retraso(row["fecha_vencimiento"], hasta)
    row = nest(nest(row, "usuario", ["id_usuario", "matricula", "nombre_completo", "rol"]),
               "libro", ["id_libro", "clave", "titulo"])
    row["dias_retraso"] = dias
    row["multa_estimada"] = circulacion.multa_retraso(dias, row.pop("multa_diaria"))
    return row


def _find(id_prestamo):
    """Préstamo con formato de API o 404.

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict: Préstamo formateado por `_shape`.

    Raises:
        ApiError: 404 si el préstamo no existe.
    """
    return _shape(or_404(model.get(id_prestamo), NO_ENCONTRADO))


def _detalle(id_prestamo):
    """Préstamo con sus renovaciones y adeudos.

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict: Préstamo más `renovaciones` y `adeudos`.

    Raises:
        ApiError: 404 si el préstamo no existe.
    """
    p = _find(id_prestamo)
    return {**p, "renovaciones": model.renovaciones(id_prestamo), "adeudos": model.adeudos(id_prestamo)}


def _folio_recibo(id_prestamo):
    """Folio del recibo de préstamo (RF-19).

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        str: Folio con formato 'REC-000012'.
    """
    return f"REC-{id_prestamo:06d}"


def _canales(valores, por_defecto=("email",)):
    """Valida los canales de envío del recibo (solo correo o WhatsApp, D-11).

    Args:
        valores: Canales solicitados (None/vacío usa `por_defecto`).
        por_defecto: Canales a usar cuando no se indica ninguno.

    Returns:
        list[str]: Canales válidos.

    Raises:
        ApiError: 400 si algún canal no es 'email' ni 'whatsapp'.
    """
    canales = notificaciones.validar_canales(valores, por_defecto)
    malos = [c for c in canales if c not in CANALES_RECIBO]
    if malos:
        raise ApiError("El recibo solo puede enviarse por correo o WhatsApp.")
    return canales


# ----------------------------------------------------------------- consultas
def listar(estado, q, matricula, limite=None):
    """Lista préstamos con filtros (RF-17).

    Args:
        estado: Estado calculado ('activo', 'vencido', 'devuelto') o vacío.
        q: Texto libre (folio, matrícula, nombre, clave, título).
        matricula: Matrícula exacta.
        limite: Tope de filas opcional.

    Returns:
        list[dict]: Préstamos formateados por `_shape`.
    """
    return [_shape(r) for r in model.list_(estado, q, matricula, limite)]


def obtener(id_prestamo):
    """Detalle de un préstamo con renovaciones y adeudos.

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict: Préstamo con `renovaciones` y `adeudos`.

    Raises:
        ApiError: 404 si no existe.
    """
    return _detalle(id_prestamo)


def _resolver(d):
    """Resuelve usuario y libro de la solicitud, o devuelve motivos si alguno no existe.

    Args:
        d: Datos validados con `matricula`, `clave` e `id_libro`.

    Returns:
        tuple: `(usuario, libro, motivos)`; `motivos` incluye USUARIO_NO_ENCONTRADO y/o
        LIBRO_NO_ENCONTRADO cuando corresponde.

    Raises:
        ApiError: 400 si no se indica clave ni id de libro.
    """
    if not d["clave"] and not d["id_libro"]:
        raise ApiError("Indica la clave del libro.")
    usuario, libro = consultas.usuario_por_matricula(d["matricula"]), model.find_libro(d["clave"], d["id_libro"])
    motivos = []
    if not usuario:
        motivos.append(motivo(USUARIO_NO_ENCONTRADO, "No existe un usuario con esa matrícula."))
    if not libro:
        motivos.append(motivo(LIBRO_NO_ENCONTRADO, "No existe un libro con esa clave."))
    return usuario, libro, motivos


def validar(payload):
    """RF-17/RF-18: valida RN-01 sin escribir; la respuesta es 200 aunque no esté autorizado.

    Args:
        payload: JSON con `matricula` y `clave` o `id_libro`.

    Returns:
        dict: `autorizado`, `motivos` (códigos RN-01: MULTAS_PENDIENTES, PRESTAMOS_VENCIDOS,
        LIMITE_EJEMPLARES, LIBRO_NO_DISPONIBLE, ...), datos de `usuario` y `libro`, `dias_prestamo`
        y `fecha_vencimiento_estimada`. Si usuario o libro no existen, `autorizado` es False con
        USUARIO_NO_ENCONTRADO / LIBRO_NO_ENCONTRADO.

    Raises:
        ApiError: 400 si el payload es inválido o no se indica libro.
    """
    d = validate(payload, SCHEMA_VALIDAR)
    usuario, libro, motivos = _resolver(d)
    if motivos:
        return {"autorizado": False, "motivos": motivos, "usuario": None, "libro": None,
                "dias_prestamo": None, "fecha_vencimiento_estimada": None}
    a = circulacion.autorizar_prestamo(usuario["id_usuario"], libro["id_libro"])
    u, pol, lib = a["usuario"], a["politica"], a["libro"]
    return {
        "autorizado": a["autorizado"], "motivos": a["motivos"],
        "usuario": {"id_usuario": u["id_usuario"], "matricula": u["matricula"], "nombre_completo": u["nombre_completo"],
                    "rol": u["rol"], "prestamos_activos": a["prestamos_abiertos"],
                    "max_libros": pol["max_libros"] if pol else None,
                    "adeudos_pendientes": a["adeudos_pendientes"], "vencidos": a["vencidos"]},
        "libro": {"id_libro": lib["id_libro"], "clave": lib["clave"], "titulo": lib["titulo"],
                  "tipo_uso": lib["tipo_uso"], "disponibles": a["disponibles"]},
        "dias_prestamo": a["dias_prestamo"], "fecha_vencimiento_estimada": a["fecha_vencimiento_estimada"],
    }


# ----------------------------------------------------------------- recibo
def recibo(id_prestamo):
    """RF-19: datos del Recibo de Préstamo + avisos enviados.

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict: `folio`, fechas, `usuario`, `libro` (con copia y ubicación), `dias_prestamo`,
        `politica` y `notificaciones` enviadas.

    Raises:
        ApiError: 404 si el préstamo o su política no existen.
    """
    p = _find(id_prestamo)
    pol = or_404(model.politica(p["id_politica"]))
    folio = _folio_recibo(id_prestamo)
    avisos = []
    for n in model.notificaciones_recibo(folio):
        avisos.append({"canal": notificaciones.parsear(n["accion"], n["detalle"])["canal"], "fecha": n["fecha"],
                       "asunto": notificaciones.parsear(n["accion"], n["detalle"])["asunto"]})
    return {"folio": folio, "fecha_prestamo": p["fecha_prestamo"], "fecha_vencimiento": p["fecha_vencimiento"],
            "usuario": p["usuario"], "libro": {**p["libro"], "numero_copia": p["numero_copia"],
                                                "ubicacion": model.ubicacion_libro(p["libro"]["id_libro"])},
            "dias_prestamo": p["dias_prestamo"],
            "politica": {"max_renovaciones": pol["max_renovaciones"], "multa_diaria": pol["multa_diaria"]},
            "notificaciones": avisos}


def _avisar(id_prestamo, canales):
    """Envía el aviso del recibo por cada canal al usuario del préstamo.

    Args:
        id_prestamo: Identificador del préstamo.
        canales: Canales ya validados.

    Returns:
        list[str]: Los mismos canales enviados.
    """
    p = _find(id_prestamo)
    folio = _folio_recibo(id_prestamo)
    cuerpo = (f"{p['libro']['titulo']} ({p['libro']['clave']}), copia {p['numero_copia']}, para {p['usuario']['nombre_completo']}. "
              f"Vence el {p['fecha_vencimiento'].strftime('%d/%m/%Y')}.")
    for canal in canales:
        notificaciones.enviar_a_usuario(canal, f"Recibo de préstamo {folio}", cuerpo, p["usuario"]["id_usuario"])
    return canales


@audit("prestamo_recibo", lambda r, a: f"Recibo {_folio_recibo(a['id_prestamo'])}: {','.join(r['enviados'])}")
def enviar_recibo(id_prestamo, payload, actor):
    """RF-19: reenvía el recibo por los canales indicados (bitácora `prestamo_recibo`).

    Args:
        id_prestamo: Identificador del préstamo.
        payload: JSON con `canales` (mínimo uno: 'email' o 'whatsapp').
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: `{"enviados": [canales]}`.

    Raises:
        ApiError: 404 si no existe el préstamo; 400 si los canales no son válidos.
    """
    _find(id_prestamo)
    canales = _canales(validate(payload, SCHEMA_ENVIAR)["canales"])
    return {"enviados": _avisar(id_prestamo, canales)}


# ----------------------------------------------------------------- prestar
@audit("prestamo_crear", lambda r: f"{r['prestamo']['folio']} {r['prestamo']['usuario']['matricula']} "
                                    f"{r['prestamo']['libro']['clave']}")
def crear(payload, actor):
    """RN-01/RN-05/RN-06: autoriza con core.circulacion, toma un ejemplar con SKIP LOCKED y emite el recibo.

    Bloquea al usuario, valida RN-01, crea el préstamo con vencimiento en días hábiles (D-03),
    marca el ejemplar 'prestado', recoge la lista de espera (D-19) y envía el recibo.

    Args:
        payload: JSON con `matricula`, `clave` o `id_libro` y `canales` opcionales.
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: `{"prestamo": detalle, "recibo": recibo}`.

    Raises:
        ApiError: 400 si el payload es inválido; 422 con `motivos` (USUARIO_NO_ENCONTRADO,
        LIBRO_NO_ENCONTRADO, o los códigos de RN-01 como LIBRO_NO_DISPONIBLE).
    """
    d = validate(payload, SCHEMA_CREAR)
    canales = _canales(d["canales"])
    usuario, libro, motivos = _resolver(d)
    exigir(motivos, "No se puede registrar el préstamo.")
    model.lock_usuario(usuario["id_usuario"])
    a = circulacion.autorizar_prestamo(usuario["id_usuario"], libro["id_libro"])
    exigir(a["motivos"], "No se puede prestar el libro.")
    ejemplar = model.take_ejemplar(libro["id_libro"])
    if not ejemplar:  # otra caja se llevo el ultimo ejemplar entre la validacion y el bloqueo
        exigir([motivo(circulacion.LIBRO_NO_DISPONIBLE, "No hay ejemplares disponibles.")],
               "No se puede prestar el libro.")
    id_prestamo = model.insert_prestamo(ejemplar["id_ejemplar"], usuario["id_usuario"], a["politica"]["id_politica"],
                                        a["fecha_vencimiento_estimada"])
    model.set_ejemplar(ejemplar["id_ejemplar"], "prestado")
    model.recoger_espera(usuario["id_usuario"], libro["id_libro"])
    _avisar(id_prestamo, canales)
    return {"prestamo": _detalle(id_prestamo), "recibo": recibo(id_prestamo)}


# ----------------------------------------------------------------- renovar
@audit("prestamo_renovar", lambda r: f"{r['prestamo']['folio']} vence {r['renovacion']['nueva_fecha_vencimiento']}")
def renovar(id_prestamo, actor):
    """RN-02/RN-06, D-05/D-06: un periodo completo sobre el vencimiento actual.

    Args:
        id_prestamo: Préstamo a renovar (se bloquea).
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: `{"prestamo": detalle, "renovacion": {"nueva_fecha_vencimiento": fecha}}`.

    Raises:
        ApiError: 404 si no existe; 422 con `motivos` (PRESTAMO_CERRADO, PRESTAMO_VENCIDO,
        MAX_RENOVACIONES, MULTAS_PENDIENTES, LISTA_ESPERA, ...).
    """
    p = or_404(model.lock_prestamo(id_prestamo), NO_ENCONTRADO)
    a = circulacion.autorizar_renovacion(id_prestamo)
    exigir(a["motivos"], "No se puede renovar el préstamo.")
    model.renovar(id_prestamo, p["num_renovaciones"] + 1, a["nueva_fecha_vencimiento"])
    return {"prestamo": _detalle(id_prestamo), "renovacion": {"nueva_fecha_vencimiento": a["nueva_fecha_vencimiento"]}}


# ----------------------------------------------------------------- devolver
@audit("prestamo_devolver", lambda r: f"{r['prestamo']['folio']} retraso {r['dias_retraso']} dia(s)")
def devolver(id_prestamo, actor):
    """RF-23/RF-24/RF-25 (retraso): ejemplar disponible al instante, adeudo por días hábiles y aviso a la espera.

    Genera un adeudo 'retraso' si hay días de retraso (RN-03, D-04) y notifica al siguiente
    de la lista de espera (D-19).

    Args:
        id_prestamo: Préstamo a cerrar (se bloquea).
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: `prestamo`, `dias_retraso`, `adeudo` (o None) y `espera_notificada` (o None).

    Raises:
        ApiError: 404 si no existe; 409 si ya fue devuelto.
    """
    p = or_404(model.lock_prestamo(id_prestamo), NO_ENCONTRADO)
    if p["fecha_devolucion"] is not None:
        raise ApiError("El préstamo ya fue devuelto.", 409)
    actual = model.get(id_prestamo)
    dias = circulacion.dias_retraso(p["fecha_vencimiento"], date.today())
    monto = circulacion.multa_retraso(dias, actual["multa_diaria"])
    circulacion.cerrar_prestamo(id_prestamo)
    model.set_ejemplar(p["id_ejemplar"], "disponible", solo_si="prestado")
    adeudo = None
    if dias > 0:
        adeudo = {"id_adeudo": model.insert_adeudo_retraso(id_prestamo, dias, monto), "monto": monto,
                  "dias_retraso": dias}
    return {"prestamo": _detalle(id_prestamo), "dias_retraso": dias, "adeudo": adeudo,
            "espera_notificada": (espera.notificar_espera(p["id_libro"]) or [None])[0]}


# ----------------------------------------------------------------- politicas
def politicas(user):
    """Lista las políticas de préstamo (D-01/D-04).

    Permite el acceso con permiso 'prestamos' o, en su defecto, 'perfiles'.

    Args:
        user: Usuario autenticado (con `permisos`).

    Returns:
        list[dict]: Políticas por rol.

    Raises:
        ApiError: 403 si no tiene ninguno de los dos permisos.
    """
    if "prestamos" not in user["permisos"]:
        require_permission("perfiles", user)
    return model.politicas()


@audit("politica_cambio", lambda r: f"Política {r['rol']}: {r['dias_prestamo']}d/{r['max_libros']}/{r['max_renovaciones']}/${r['multa_diaria']}")
def actualizar_politica(id_politica, payload, actor):
    """Actualiza una política de préstamo (D-01/D-04), registrada en bitácora `politica_cambio`.

    Args:
        id_politica: Política a modificar.
        payload: JSON con `dias_prestamo`, `max_libros`, `max_renovaciones` y `multa_diaria`.
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: Política actualizada.

    Raises:
        ApiError: 404 si no existe; 400 si algún valor está fuera de rango.
    """
    or_404(model.politica(id_politica), "No se encontró la política.")
    model.update_politica(id_politica, validate(payload, SCHEMA_POLITICA))
    return model.politica(id_politica)
