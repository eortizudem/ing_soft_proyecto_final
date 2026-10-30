"""Servicio de adeudos: reglas de negocio (capa service del MVC).

Pago en Tesorería (D-10, RF-27), cancelación solo admin (D-04), pérdida (RN-04/D-07)
y daño (D-08), con notificaciones simuladas (D-11) y bitácora (`@audit`).
Errores con `ApiError` (400 validación, 403 permiso, 404, 409 conflicto).
"""
from datetime import date
from decimal import Decimal

from app.core import circulacion, espera, notificaciones, parametros
from app.core.bitacora import audit
from app.core.errors import ApiError
from app.core.repo import or_404
from app.core.validators import Bool, Date, Dec, Int, Str, validate

from . import model

ESTADOS = ("pendiente", "pagado", "cancelado")
TIPOS = ("retraso", "danio", "perdida")
NO_ENCONTRADO = "No se encontró el adeudo."
NO_PRESTAMO = "No se encontró el préstamo."

_TC = Dec(Decimal("0.0001"), Decimal("10000"), required=False, msg="El tipo de cambio debe ser un número mayor que 0.")
_OBS = Str("observación", max=100, required=False)
_PORC = Int(*circulacion.PORCENTAJE_DANIO_RANGO, required=False, default=circulacion.PORCENTAJE_DANIO_DEFAULT,
            msg="El porcentaje de daño debe estar entre 10 y 100.")

SCHEMA_PAGO = {
    "referencia_tesoreria": Str("referencia de Tesorería", min=3, max=40,
                                min_msg="La referencia de Tesorería necesita de 3 a 40 caracteres.",
                                max_msg="La referencia de Tesorería necesita de 3 a 40 caracteres.",
                                required_msg="La referencia de Tesorería es obligatoria."),
    "fecha_pago": Date(max=None, required=False, msg="La fecha de pago no es válida."),
}
SCHEMA_CANCELAR = {"motivo": Str("motivo", min=3, max=120, required_msg="El motivo de la cancelación es obligatorio.",
                                 min_msg="El motivo necesita de 3 a 120 caracteres.",
                                 max_msg="El motivo necesita de 3 a 120 caracteres.")}
SCHEMA_PERDIDA = {"id_prestamo": Int(1, msg="Indica el préstamo."), "tipo_cambio": _TC, "observacion": _OBS}
SCHEMA_DANIO = {"id_prestamo": Int(1, msg="Indica el préstamo."), "porcentaje": _PORC, "observacion": _OBS,
                "dar_baja": Bool(required=False, default=False, msg="dar_baja debe ser verdadero o falso.")}


def listar(estado, tipo, q, matricula, limite=None):
    """Lista adeudos con filtros.

    Args:
        estado: 'pendiente', 'pagado', 'cancelado' o vacío.
        tipo: 'retraso', 'danio', 'perdida' o vacío.
        q: Texto libre.
        matricula: Matrícula exacta.
        limite: Tope de filas opcional.

    Returns:
        list[dict]: Adeudos con `usuario` y `libro` anidados.
    """
    return model.list_(estado, tipo, q, matricula, limite)


def obtener(id_adeudo):
    """Detalle de un adeudo con referencia de Tesorería y motivo de cancelación (de bitácora).

    Args:
        id_adeudo: Identificador del adeudo.

    Returns:
        dict: Adeudo con `referencia_tesoreria` y `motivo_cancelacion` (None si no aplican).

    Raises:
        ApiError: 404 si no existe.
    """
    a = or_404(model.get(id_adeudo), NO_ENCONTRADO)
    pago = model.bitacora_de("adeudo_pago", id_adeudo)
    cond = model.bitacora_de("adeudo_cancelar", id_adeudo)
    a["referencia_tesoreria"] = pago["detalle"].split("ref ", 1)[-1] if pago else None
    a["motivo_cancelacion"] = cond["detalle"].split(": ", 1)[-1] if cond else None
    return a


def tipo_cambio():
    """Tipo de cambio USD/MXN vigente (simulado, D-28).

    Returns:
        dict: `usd_mxn`, `fuente` ('simulado') y `nota`.
    """
    return {"usd_mxn": parametros.tipo_cambio(), "fuente": "simulado",
            "nota": "Tipo de cambio simulado (Banxico FIX); configurable con TIPO_CAMBIO_USD_MXN."}


def reposicion(id_libro, tc=None):
    """Valor de reposición de un libro (RN-04, D-07): última compra recibida en USD x tipo de cambio.

    Args:
        id_libro: Libro a valorar.
        tc: Tipo de cambio opcional (Decimal); None usa el vigente.

    Returns:
        dict: Resultado de `circulacion.valor_reposicion` (`valor_usd`, `tipo_cambio`, `monto_mxn`, `fuente`).

    Raises:
        ApiError: 400 si no se indica el libro.
    """
    if not id_libro:
        raise ApiError("Indica el libro (id_libro).")
    return circulacion.valor_reposicion(id_libro, tc)


def _prestamo_abierto(id_prestamo):
    """Préstamo bloqueado que aún no ha sido cerrado.

    Args:
        id_prestamo: Identificador del préstamo.

    Returns:
        dict: Datos de `model.lock_loan`.

    Raises:
        ApiError: 404 si no existe; 409 si ya está cerrado.
    """
    p = or_404(model.lock_loan(id_prestamo), NO_PRESTAMO)
    if p["fecha_devolucion"] is not None or p["estado"] == "devuelto":
        raise ApiError("El préstamo ya está cerrado.", 409)
    return p


def _retraso(p, hoy):
    """Días hábiles de retraso y multa de un préstamo a una fecha (RN-03, D-04).

    Args:
        p: Préstamo de `model.lock_loan`.
        hoy: Fecha de corte.

    Returns:
        tuple[int, Decimal]: `(dias, multa)`.
    """
    dias = circulacion.dias_retraso(p["fecha_vencimiento"], hoy)
    return dias, circulacion.multa_retraso(dias, p["multa_diaria"])


def previsualizar(id_prestamo, args):
    """Datos del préstamo y montos calculados (sin escribir) para confirmar pérdida o daño.

    Args:
        id_prestamo: Préstamo a consultar.
        args: Query con `tipo_cambio` y `porcentaje` opcionales.

    Returns:
        dict: Usuario, libro, retraso, `reposicion`, `porcentaje` y `monto_danio`.

    Raises:
        ApiError: 400 parámetros inválidos (tipo de cambio o porcentaje fuera de 10-100); 404 si no existe.
    """
    d = validate(args, {"tipo_cambio": _TC, "porcentaje": _PORC})
    p = or_404(model.lock_loan(id_prestamo), NO_PRESTAMO)
    rep = circulacion.valor_reposicion(p["id_libro"], d["tipo_cambio"])
    dias, multa = _retraso(p, date.today())
    abierto = p["fecha_devolucion"] is None
    return {"id_prestamo": p["id_prestamo"], "abierto": abierto,
            "usuario": {"matricula": p["matricula"], "nombre_completo": p["nombre_completo"]},
            "libro": {"id_libro": p["id_libro"], "clave": p["clave"], "titulo": p["titulo"]},
            "numero_copia": p["numero_copia"], "fecha_vencimiento": p["fecha_vencimiento"],
            "dias_retraso": dias if abierto else 0, "monto_retraso": multa if abierto else Decimal("0.00"),
            "reposicion": rep, "porcentaje": d["porcentaje"],
            "monto_danio": circulacion.monto_danio(rep["monto_mxn"], d["porcentaje"])}


@audit("adeudo_pago", lambda r: f"adeudo {r['id_adeudo']}: ref {r['referencia_tesoreria']}")
def pagar(id_adeudo, d, actor):
    """Registra el pago de un adeudo pendiente en Tesorería (D-10, RF-27) y avisa por correo.

    Args:
        id_adeudo: Adeudo a pagar.
        d: JSON con `referencia_tesoreria` (3-40 caracteres) y `fecha_pago` opcional (no futura).
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: Adeudo actualizado con `referencia_tesoreria`.

    Raises:
        ApiError: 400 payload o fecha inválida/futura; 404 no existe; 409 si ya no está pendiente.
    """
    data = validate(d, SCHEMA_PAGO)
    a = or_404(model.get(id_adeudo), NO_ENCONTRADO)
    fecha = data["fecha_pago"] or date.today()
    if fecha > date.today():
        raise ApiError("La fecha de pago no puede ser futura.")
    if a["estado"] != "pendiente" or not model.mark_paid(id_adeudo, fecha):
        raise ApiError(f"El adeudo ya está {a['estado']}.", 409)
    notificaciones.enviar_a_usuario(
        "email", "Pago de adeudo registrado",
        f"Se registró el pago del adeudo {id_adeudo} por ${a['monto']:.2f} MXN (ref. {data['referencia_tesoreria']}).",
        a["usuario"]["id_usuario"])
    return {**obtener(id_adeudo), "referencia_tesoreria": data["referencia_tesoreria"]}


@audit("adeudo_cancelar", lambda r: f"adeudo {r['id_adeudo']}: {r['motivo_cancelacion']}")
def cancelar(id_adeudo, d, actor):
    """Cancela un adeudo pendiente; exclusivo del administrador (D-04).

    Args:
        id_adeudo: Adeudo a cancelar.
        d: JSON con `motivo` (3-120 caracteres).
        actor: Usuario autenticado; debe tener rol 'admin'.

    Returns:
        dict: Adeudo actualizado con `motivo_cancelacion`.

    Raises:
        ApiError: 403 si no es admin; 400 payload inválido; 404 no existe; 409 si ya no está pendiente.
    """
    if actor["rol"] != "admin":
        raise ApiError("Solo el administrador puede cancelar adeudos.", 403)
    data = validate(d, SCHEMA_CANCELAR)
    a = or_404(model.get(id_adeudo), NO_ENCONTRADO)
    if a["estado"] != "pendiente" or not model.mark_cancelled(id_adeudo):
        raise ApiError(f"El adeudo ya está {a['estado']}.", 409)
    return {**obtener(id_adeudo), "motivo_cancelacion": data["motivo"]}


def _retraso_adeudo(p, hoy):
    """Crea el adeudo 'retraso' si hay días de retraso (RN-03).

    Args:
        p: Préstamo de `model.lock_loan`.
        hoy: Fecha de corte.

    Returns:
        dict | None: Adeudo creado, o None si no hay retraso.
    """
    dias, multa = _retraso(p, hoy)
    return model.add_debt(p["id_prestamo"], "retraso", multa, dias) if dias > 0 else None


@audit("adeudo_perdida", lambda r: f"prestamo {r['id_prestamo']}: ${r['monto_mxn']:.2f}")
def perdida(d, actor):
    """Registra la pérdida de un ejemplar (RN-04, D-07).

    Crea el adeudo de retraso (si aplica) y el de reposición, da de baja el ejemplar
    ('perdido'), cierra el préstamo y notifica a Servicios Escolares, Tesorería y al usuario.

    Args:
        d: JSON con `id_prestamo`, `tipo_cambio` y `observacion` opcionales.
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: `id_prestamo`, `adeudos`, `valor_usd`, `tipo_cambio`, `monto_mxn` y `fuente`.

    Raises:
        ApiError: 400 payload inválido; 404 préstamo inexistente; 409 préstamo ya cerrado.
    """
    data = validate(d, SCHEMA_PERDIDA)
    p = _prestamo_abierto(data["id_prestamo"])
    rep = circulacion.valor_reposicion(p["id_libro"], data["tipo_cambio"])
    adeudos = [a for a in (_retraso_adeudo(p, date.today()),
                           model.add_debt(p["id_prestamo"], "perdida", rep["monto_mxn"])) if a]
    model.set_copy(p["id_ejemplar"], "baja", "perdido")
    circulacion.cerrar_prestamo(p["id_prestamo"])
    asunto = "Pérdida de material bibliográfico"
    cuerpo = (f"{p['matricula']} {p['nombre_completo']} perdió «{p['titulo']}» (copia {p['numero_copia']}). "
              f"Reposición ${rep['monto_mxn']:.2f} MXN ({rep['valor_usd']} USD x {rep['tipo_cambio']}).")
    for canal, destino in (("servicios_escolares", "Servicios Escolares"), ("tesoreria", "Tesorería")):
        notificaciones.enviar(canal, asunto, cuerpo, actor["id_usuario"], destino)
    notificaciones.enviar_a_usuario("email", asunto, f"Se registró la pérdida de «{p['titulo']}». "
                                    f"Adeudo por ${rep['monto_mxn']:.2f} MXN.", p["id_usuario"])
    return {"id_prestamo": p["id_prestamo"], "adeudos": adeudos, "valor_usd": rep["valor_usd"],
            "tipo_cambio": rep["tipo_cambio"], "monto_mxn": rep["monto_mxn"], "fuente": rep["fuente"]}


@audit("adeudo_danio", lambda r: f"prestamo {r['devolucion']['id_prestamo']}: ${r['adeudo']['monto']:.2f}")
def danio(d, actor):
    """Registra el daño de un ejemplar (D-08, RF-25).

    Adeudo = porcentaje (10-100 %, 50 % por defecto) del valor de reposición, más retraso si aplica.
    Con `dar_baja` el ejemplar queda en baja ('danado'); si no, vuelve a disponible y se avisa a la espera.

    Args:
        d: JSON con `id_prestamo`, `porcentaje`, `observacion` y `dar_baja` opcionales.
        actor: Usuario autenticado que ejecuta la acción.

    Returns:
        dict: `adeudo`, `porcentaje`, `valor_reposicion`, `devolucion` y `espera_notificada`.

    Raises:
        ApiError: 400 payload o porcentaje inválido; 404 préstamo inexistente; 409 préstamo ya cerrado.
    """
    data = validate(d, SCHEMA_DANIO)
    p = _prestamo_abierto(data["id_prestamo"])
    rep = circulacion.valor_reposicion(p["id_libro"])
    monto = circulacion.monto_danio(rep["monto_mxn"], data["porcentaje"])
    retraso = _retraso_adeudo(p, date.today())
    adeudo = model.add_debt(p["id_prestamo"], "danio", monto)
    estado_ejemplar, motivo = ("baja", "danado") if data["dar_baja"] else ("disponible", None)
    model.set_copy(p["id_ejemplar"], estado_ejemplar, motivo)
    circulacion.cerrar_prestamo(p["id_prestamo"])
    notificaciones.enviar_a_usuario("email", "Daño de material bibliográfico",
                                    f"Se registró daño en «{p['titulo']}». Adeudo por ${monto:.2f} MXN.",
                                    p["id_usuario"])
    espera_notificada = espera.notificar_espera(p["id_libro"]) if estado_ejemplar == "disponible" else []
    return {"adeudo": adeudo, "porcentaje": data["porcentaje"], "valor_reposicion": rep["monto_mxn"],
            "devolucion": {"id_prestamo": p["id_prestamo"], "dias_retraso": retraso["dias_retraso"] if retraso else 0,
                           "adeudo_retraso": retraso, "ejemplar_estado": estado_ejemplar},
            "espera_notificada": espera_notificada[0] if espera_notificada else None}
