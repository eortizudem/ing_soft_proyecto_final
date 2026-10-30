"""Reglas de circulacion compartidas (RN-01..RN-06, D-01..D-09, D-24). Prestamos, espera, adeudos y asistente
deben llamar a ESTE codigo; ningun modulo reimplementa vencimientos, multas, elegibilidad ni reposicion.

Dos capas (mas una escritura compartida minima, `cerrar_prestamo`):
  * Reglas puras (sin BD): `fecha_vencimiento`, `dias_retraso`, `multa_retraso`, `esta_vencido`,
    `evaluar_prestamo`, `evaluar_renovacion`, `fecha_renovacion`, `limite_reserva`, `valor_reposicion_mxn`, `monto_danio`.
    Devuelven valores o listas de motivos `[{codigo, mensaje}]` (lista vacia = permitido).
  * Lectura de contexto (SQL de solo lectura, requiere contexto de app): `contexto_usuario`, `contexto_libro`,
    `autorizar_prestamo`, `autorizar_renovacion`, `valor_reposicion`. Escriben NADA; las escrituras son del modulo dueno.

Definicion unica de vencido (D-24): `fecha_devolucion IS NULL AND fecha_vencimiento < hoy`. `prestamo.estado='vencido'`
es solo cache; nunca se usa para decidir. Para convertir motivos en 422: `core.errors.exigir(motivos)`.
"""
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from . import db, parametros, repo
from .calendario import habiles_entre, sumar_habiles
from .errors import ApiError, motivo

CENT = Decimal("0.01")
PORCENTAJE_DANIO_DEFAULT = 50          # D-08
PORCENTAJE_DANIO_RANGO = (10, 100)
TIPOS_USO_PRESTABLES = ("prestamo_externo",)

# Codigos de motivo (contrato con el frontend y las pruebas)
USUARIO_INACTIVO = "USUARIO_INACTIVO"
SIN_POLITICA = "SIN_POLITICA"
MULTAS_PENDIENTES = "MULTAS_PENDIENTES"
PRESTAMOS_VENCIDOS = "PRESTAMOS_VENCIDOS"
LIMITE_EJEMPLARES = "LIMITE_EJEMPLARES"
LIBRO_INACTIVO = "LIBRO_INACTIVO"
LIBRO_NO_PRESTABLE = "LIBRO_NO_PRESTABLE"
LIBRO_NO_DISPONIBLE = "LIBRO_NO_DISPONIBLE"
LIBRO_RESERVADO_OTRO_USUARIO = "LIBRO_RESERVADO_OTRO_USUARIO"
PRESTAMO_CERRADO = "PRESTAMO_CERRADO"
PRESTAMO_VENCIDO = "PRESTAMO_VENCIDO"
MAX_RENOVACIONES = "MAX_RENOVACIONES"
LISTA_ESPERA = "LISTA_ESPERA"


def _hoy(hoy):
    """`hoy` o la fecha actual si es None."""
    return hoy or date.today()


def _dia(x):
    """Normaliza datetime a date."""
    return x.date() if isinstance(x, datetime) else x


def redondear(x) -> Decimal:
    """Importe a 2 decimales (mitad hacia arriba)."""
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


# ============================== reglas puras ==============================

def fecha_vencimiento(fecha_prestamo, dias_prestamo) -> date:
    """RN-05/RN-06 + D-03: `dias_prestamo` dias habiles despues del prestamo (inclusivo)."""
    return sumar_habiles(_dia(fecha_prestamo), int(dias_prestamo))


def dias_retraso(vencimiento, hasta) -> int:
    """Dias habiles de retraso en (vencimiento, hasta]; devolver el dia de vencimiento no genera multa."""
    return habiles_entre(_dia(vencimiento), _dia(hasta))


def multa_retraso(dias, multa_diaria) -> Decimal:
    """RN-03/D-04: dias habiles x tarifa diaria, sin tope."""
    return redondear(Decimal(int(dias)) * Decimal(str(multa_diaria)))


def esta_vencido(vencimiento, devolucion=None, hoy=None) -> bool:
    """D-24."""
    return devolucion is None and _dia(vencimiento) < _hoy(hoy)


def evaluar_prestamo(*, usuario_activo, politica, prestamos_abiertos, vencidos, adeudos_pendientes,
                     libro_activo, tipo_uso, disponibles, reservados=0, usuario_notificado=False):
    """RN-01 (+D-01/D-02): motivos por los que NO se puede prestar. Lista vacia = autorizado.

    politica: dict con `max_libros` o None. adeudos_pendientes/vencidos/prestamos_abiertos: conteos.
    reservados: ejemplares reservados por la lista de espera (D-19); usuario_notificado: el solicitante es
    quien tiene el reservado.
    """
    m = []
    if not usuario_activo:
        m.append(motivo(USUARIO_INACTIVO, "El usuario está inactivo."))
    if not politica:
        m.append(motivo(SIN_POLITICA, "El perfil del usuario no tiene una política de préstamo activa."))
    if adeudos_pendientes:
        m.append(motivo(MULTAS_PENDIENTES, "El usuario tiene multas o adeudos pendientes."))
    if vencidos:
        m.append(motivo(PRESTAMOS_VENCIDOS, "El usuario tiene préstamos vencidos sin devolver."))
    if politica and prestamos_abiertos >= politica["max_libros"]:
        m.append(motivo(LIMITE_EJEMPLARES, f"El usuario ya tiene el máximo de {politica['max_libros']} libro(s) en préstamo."))
    if not libro_activo:
        m.append(motivo(LIBRO_INACTIVO, "El libro está inactivo en el catálogo."))
    elif tipo_uso not in TIPOS_USO_PRESTABLES:
        m.append(motivo(LIBRO_NO_PRESTABLE, "El libro no es de préstamo externo (consulta interna o reservado)."))
    elif disponibles <= 0:
        m.append(motivo(LIBRO_NO_DISPONIBLE, "No hay ejemplares disponibles."))
    elif not usuario_notificado and disponibles - reservados <= 0:
        m.append(motivo(LIBRO_RESERVADO_OTRO_USUARIO, "Los ejemplares disponibles están reservados para quien espera."))
    return m


def evaluar_renovacion(*, abierto, vencido, num_renovaciones, max_renovaciones, adeudos_pendientes, espera_activa):
    """RN-02/RN-06 + D-05: motivos por los que NO se puede renovar. Lista vacia = permitido."""
    if not abierto:
        return [motivo(PRESTAMO_CERRADO, "El préstamo ya fue devuelto.")]
    m = []
    if vencido:
        m.append(motivo(PRESTAMO_VENCIDO, "El préstamo está vencido; devuélvelo."))
    if num_renovaciones >= max_renovaciones:
        m.append(motivo(MAX_RENOVACIONES, f"Se alcanzó el máximo de {max_renovaciones} renovación(es)."))
    if adeudos_pendientes:
        m.append(motivo(MULTAS_PENDIENTES, "El usuario tiene multas o adeudos pendientes."))
    if espera_activa:
        m.append(motivo(LISTA_ESPERA, "Hay usuarios en lista de espera de este libro."))
    return m


def fecha_renovacion(vencimiento_actual, dias_prestamo) -> date:
    """D-05: un periodo completo (dias habiles) sobre la fecha de vencimiento ACTUAL."""
    return sumar_habiles(_dia(vencimiento_actual), int(dias_prestamo))


def limite_reserva(desde=None) -> datetime:
    """D-19: fin del dia (23:59:59) tras `dias_reserva_espera()` dias habiles; valor de
    `lista_espera.fecha_limite_recoger`. Lo usan prestamos (al notificar) y espera (al expirar/avanzar)."""
    return datetime.combine(sumar_habiles(_hoy(desde), parametros.dias_reserva_espera()), time(23, 59, 59))


def valor_reposicion_mxn(valor_usd, tipo_cambio) -> Decimal:
    """RN-04/D-07: USD x tipo de cambio, 2 decimales."""
    return redondear(Decimal(str(valor_usd)) * Decimal(str(tipo_cambio)))


def monto_danio(monto_reposicion, porcentaje=PORCENTAJE_DANIO_DEFAULT) -> Decimal:
    """D-08: porcentaje (10-100, por defecto 50) del valor de reposicion."""
    lo, hi = PORCENTAJE_DANIO_RANGO
    if not lo <= porcentaje <= hi:
        raise ApiError(f"El porcentaje de daño debe estar entre {lo} y {hi}.")
    return redondear(Decimal(str(monto_reposicion)) * Decimal(str(porcentaje)) / 100)


# ============================== contexto desde la BD (solo lectura) ==============================

def politica_vigente(id_rol):
    """Politica activa mas reciente del rol (o None)."""
    return db.fetchone("SELECT * FROM politica_prestamo WHERE id_rol=%s AND activa "
                       "ORDER BY vigente_desde DESC, id_politica DESC LIMIT 1", (id_rol,))


def contexto_usuario(id_usuario, hoy=None):
    """Estado de circulacion del usuario: datos, politica, conteos y `suspendido` (D-09). 404 si no existe."""
    u = db.fetchone("SELECT u.id_usuario, u.matricula, u.nombre_completo, u.correo, u.estado, u.id_rol, r.nombre AS rol "
                    "FROM usuario u JOIN rol r ON r.id_rol=u.id_rol WHERE u.id_usuario=%s", (id_usuario,))
    if not u:
        raise ApiError("No se encontró el usuario.", 404)
    c = db.fetchone(
        """SELECT count(*) FILTER (WHERE fecha_devolucion IS NULL) AS abiertos,
                  count(*) FILTER (WHERE fecha_devolucion IS NULL AND fecha_vencimiento < %s) AS vencidos
           FROM prestamo WHERE id_usuario=%s""", (_hoy(hoy), id_usuario))
    a = db.fetchone(
        """SELECT count(*) AS n, COALESCE(sum(a.monto), 0) AS monto FROM adeudo a
           JOIN prestamo p ON p.id_prestamo=a.id_prestamo WHERE p.id_usuario=%s AND a.estado='pendiente'""", (id_usuario,))
    return {"usuario": u, "politica": politica_vigente(u["id_rol"]), "prestamos_abiertos": c["abiertos"],
            "vencidos": c["vencidos"], "adeudos_pendientes": a["n"], "adeudos_monto": a["monto"],
            "suspendido": bool(c["vencidos"] or a["n"])}


def contexto_libro(id_libro, id_usuario=None):
    """Libro + `disponibles` (ejemplares 'disponible'), `reservados` (espera 'notificado' vigente, D-19) y si
    `id_usuario` es quien tiene el libro reservado. 404 si no existe."""
    libro = repo.get_or_404("libro", "id_libro", id_libro, "No se encontró el libro.")
    r = db.fetchone(
        """SELECT (SELECT count(*) FROM ejemplar WHERE id_libro=%(l)s AND estado='disponible') AS disponibles,
                  (SELECT count(*) FROM lista_espera WHERE id_libro=%(l)s AND estado='notificado'
                     AND (fecha_limite_recoger IS NULL OR fecha_limite_recoger >= now())) AS reservados,
                  (SELECT count(*) FROM lista_espera WHERE id_libro=%(l)s AND id_usuario=%(u)s AND estado='notificado'
                     AND (fecha_limite_recoger IS NULL OR fecha_limite_recoger >= now())) AS propio""",
        {"l": id_libro, "u": id_usuario})
    return {"libro": libro, "disponibles": r["disponibles"], "reservados": r["reservados"],
            "usuario_notificado": r["propio"] > 0}


def autorizar_prestamo(id_usuario, id_libro, hoy=None):
    """RN-01 completa: `{autorizado, motivos, usuario, politica, libro, disponibles, reservados, dias_prestamo,
    fecha_vencimiento_estimada, prestamos_abiertos, vencidos, adeudos_pendientes, adeudos_monto}`."""
    cu, cl = contexto_usuario(id_usuario, hoy), contexto_libro(id_libro, id_usuario)
    u, pol, lib = cu["usuario"], cu["politica"], cl["libro"]
    motivos = evaluar_prestamo(
        usuario_activo=u["estado"] == "activo", politica=pol, prestamos_abiertos=cu["prestamos_abiertos"],
        vencidos=cu["vencidos"], adeudos_pendientes=cu["adeudos_pendientes"], libro_activo=lib["estado"] == "activo",
        tipo_uso=lib["tipo_uso"], disponibles=cl["disponibles"], reservados=cl["reservados"],
        usuario_notificado=cl["usuario_notificado"])
    dias = pol["dias_prestamo"] if pol else None
    return {**cu, **{k: cl[k] for k in ("libro", "disponibles", "reservados")}, "motivos": motivos,
            "autorizado": not motivos, "dias_prestamo": dias,
            "fecha_vencimiento_estimada": fecha_vencimiento(_hoy(hoy), dias) if dias else None}


def autorizar_renovacion(id_prestamo, hoy=None):
    """RN-02/RN-06 sobre un prestamo existente (usa la politica con la que se creo, D-05):
    `{permitido, motivos, prestamo, max_renovaciones, dias_prestamo, nueva_fecha_vencimiento, dias_retraso}`."""
    p = db.fetchone(
        """SELECT p.*, e.id_libro, pol.dias_prestamo, pol.max_renovaciones, pol.multa_diaria
           FROM prestamo p JOIN ejemplar e ON e.id_ejemplar=p.id_ejemplar
           JOIN politica_prestamo pol ON pol.id_politica=p.id_politica WHERE p.id_prestamo=%s""", (id_prestamo,))
    if not p:
        raise ApiError("No se encontró el préstamo.", 404)
    adeudos = db.fetchone(
        """SELECT count(*) AS n FROM adeudo a JOIN prestamo x ON x.id_prestamo=a.id_prestamo
           WHERE x.id_usuario=%s AND a.estado='pendiente'""", (p["id_usuario"],))["n"]
    espera = db.fetchone("SELECT count(*) AS n FROM lista_espera WHERE id_libro=%s AND estado IN ('en_espera','notificado')",
                         (p["id_libro"],))["n"]
    hoy = _hoy(hoy)
    abierto = p["fecha_devolucion"] is None
    motivos = evaluar_renovacion(
        abierto=abierto, vencido=esta_vencido(p["fecha_vencimiento"], p["fecha_devolucion"], hoy),
        num_renovaciones=p["num_renovaciones"], max_renovaciones=p["max_renovaciones"],
        adeudos_pendientes=adeudos, espera_activa=espera)
    return {"permitido": not motivos, "motivos": motivos, "prestamo": p, "max_renovaciones": p["max_renovaciones"],
            "dias_prestamo": p["dias_prestamo"],
            "nueva_fecha_vencimiento": fecha_renovacion(p["fecha_vencimiento"], p["dias_prestamo"]),
            "dias_retraso": dias_retraso(p["fecha_vencimiento"], hoy) if abierto else 0}


def valor_reposicion(id_libro, tipo_cambio=None):
    """RN-04/D-07: `{id_libro, valor_usd, fuente, tipo_cambio, monto_mxn}`. valor_usd = precio_unitario de la ultima
    compra recibida del libro ('ultima_compra'), o libro.precio_referencia ('precio_referencia')."""
    libro = repo.get_or_404("libro", "id_libro", id_libro, "No se encontró el libro.")
    ultima = db.fetchone(
        """SELECT d.precio_unitario FROM detalle_solicitud d JOIN solicitud_compra s ON s.id_solicitud=d.id_solicitud
           WHERE d.id_libro=%s AND s.estado='recibida'
           ORDER BY s.fecha_recepcion DESC NULLS LAST, d.id_detalle DESC LIMIT 1""", (id_libro,))
    valor, fuente = ((ultima["precio_unitario"], "ultima_compra") if ultima
                     else (libro["precio_referencia"], "precio_referencia"))
    tc = Decimal(str(tipo_cambio)) if tipo_cambio is not None else parametros.tipo_cambio()
    return {"id_libro": id_libro, "valor_usd": Decimal(valor), "fuente": fuente, "tipo_cambio": tc,
            "monto_mxn": valor_reposicion_mxn(valor, tc)}


def cerrar_prestamo(id_prestamo):
    """Registra la devolucion (`fecha_devolucion=now()`, `estado='devuelto'`). Unica escritura de cierre: la usan
    prestamos (devolver) y adeudos (perdida/dano)."""
    db.execute("UPDATE prestamo SET estado='devuelto', fecha_devolucion=now() WHERE id_prestamo=%s", (id_prestamo,))
