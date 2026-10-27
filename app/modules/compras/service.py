from datetime import date
from decimal import Decimal

from app.core.bitacora import audit
from app.core import notificaciones, parametros
from app.core.errors import ApiError, exigir, motivo
from app.core.repo import or_404
from app.core.validators import Date, Dec, Int, List, Str, validate
from app.modules.catalogo.model import add_ejemplares

from . import model

MAX_TOTAL = Decimal("9999999999.99")

LINEA = {
    "descripcion": Str("título", max=200),
    "cantidad": Int(1, 10000, msg="La cantidad de cada título debe ser un entero entre 1 y 10000."),
    "precio_unitario": Dec(0, 10000000, places=2, msg="Introduce un precio unitario válido."),
}
SCHEMA = {
    "justificacion": Str("justificación", max=200),
    "destinatario": Str("destinatario", max=60, required=False, default="Tesorería",
                        max_msg="El campo «Para» admite máximo 60 caracteres."),
    "detalles": List(LINEA, min=1, msg="Agrega por lo menos un título."),
}


RECIBIR_PEDIDO = {
    "factura_folio": Str("folio de factura", min=3, max=30,
                         max_msg="El folio de factura admite máximo 30 caracteres.",
                         min_msg="El folio de factura debe tener al menos 3 caracteres."),
    "factura_total": Dec(0, MAX_TOTAL, places=2, msg="Introduce un monto de factura válido."),
    "fecha_recepcion": Date(label="fecha en que llegó el pedido", required=False),
    "lineas": List({
        "id_detalle": Int(1, None, msg="Línea de solicitud no válida."),
        "cantidad_recibida": Int(0, 10000, msg="La cantidad recibida debe ser un entero entre 0 y 10000."),
    }, min=1, msg="Indica las cantidades recibidas."),
}


def _mes(valor):
    """'YYYY-MM' (o None = mes actual) -> date del primer dia."""
    if valor in (None, ""):
        h = model.hoy()
        return h.replace(day=1)
    try:
        y, m = str(valor).split("-")
        return date(int(y), int(m), 1)
    except ValueError:
        raise ApiError("El mes debe tener el formato AAAA-MM.")


def presupuesto(mes=None):
    """RF-05/D-22: presupuesto del mes, usado (no canceladas) y disponible."""
    d = _mes(mes)
    total = parametros.presupuesto_mensual()
    usado = Decimal(model.usado_mes(d))
    return {"mes": d.strftime("%Y-%m"), "presupuesto_usd": total, "usado_usd": usado,
            "disponible_usd": total - usado}


def listar():
    return model.list_()


def obtener(id_solicitud):
    return or_404(model.get(id_solicitud), "No se encontró la solicitud.")


@audit("compra_crear", lambda s: f"Solicitud {s['folio']} por ${s['total_estimado']}")
def crear(d, actor):
    data = validate(d, SCHEMA)
    total = sum((x["cantidad"] * x["precio_unitario"] for x in data["detalles"]), Decimal(0))
    if total > MAX_TOTAL:
        raise ApiError("El total estimado excede el máximo permitido.")
    model.lock_presupuesto()
    disp = presupuesto()["disponible_usd"]
    exigir([motivo("PRESUPUESTO_EXCEDIDO",
                   f"El total (USD {total:,.2f}) excede el presupuesto disponible del mes (USD {max(disp, Decimal(0)):,.2f}).")]
           if total > disp else [], "La solicitud excede el presupuesto mensual.")
    folio = model.next_folio()
    sid = model.insert(folio, actor["id_usuario"], data["justificacion"], data["destinatario"], total)
    for x in data["detalles"]:
        model.insert_detalle(sid, x["descripcion"], x["cantidad"], x["precio_unitario"])
    return model.get(sid)


@audit("compra_enviar", lambda s: f"Solicitud {s['folio']} enviada a {s['destinatario']}")
def enviar(id_solicitud, actor):
    s = obtener(id_solicitud)
    if s["estado"] != "pendiente":
        raise ApiError("Solo se pueden enviar solicitudes pendientes.")
    model.set_estado(id_solicitud, "enviada")
    return model.get(id_solicitud)


@audit("compra_cancelar", lambda s: f"Solicitud {s['folio']} cancelada")
def cancelar(id_solicitud, actor):
    s = obtener(id_solicitud)
    if s["estado"] not in ("pendiente", "enviada"):
        raise ApiError("Solo se pueden cancelar solicitudes pendientes o enviadas.", 409)
    if model.total_recibido(id_solicitud) > 0:
        raise ApiError("La solicitud ya tiene pedidos recibidos y no se puede cancelar.", 409)
    model.set_estado(id_solicitud, "cancelada")
    return model.get(id_solicitud)


@audit("compra_recibir", lambda s: f"Solicitud {s['folio']} factura {s['factura_folio']} ({s['estado']})")
def recibir(id_solicitud, d, actor):
    """RF-06/D-25: recibir el pedido (parcial o total) con factura; ejemplares para lineas con libro."""
    s = obtener(id_solicitud)
    if s["estado"] != "enviada":
        raise ApiError("Solo se pueden recibir solicitudes enviadas.", 409)
    data = validate(d, RECIBIR_PEDIDO)
    recepcion = data.get("fecha_recepcion") or model.hoy()
    if recepcion > model.hoy():
        raise ApiError("La fecha en que llegó el pedido no puede ser futura.")
    detalles = {x["id_detalle"]: x for x in model.lock_detalles(id_solicitud)}
    recibido = {}
    for l in data["lineas"]:
        if l["id_detalle"] not in detalles:
            raise ApiError("Una de las líneas no pertenece a la solicitud.")
        if l["id_detalle"] in recibido:
            raise ApiError("Hay líneas repetidas al recibir el pedido.")
        recibido[l["id_detalle"]] = l["cantidad_recibida"]
    if not any(recibido.values()):
        raise ApiError("Indica al menos un ejemplar recibido.")
    pendientes = []
    for id_detalle, n in recibido.items():
        x = detalles[id_detalle]
        if n == 0:
            continue
        if x["cantidad_recibida"] + n > x["cantidad"]:
            raise ApiError(f"«{x['descripcion']}»: la cantidad recibida excede la pedida "
                           f"({x['cantidad_recibida']} de {x['cantidad']} ya recibidos).")
        model.sumar_recibido(id_detalle, n)
        x["cantidad_recibida"] += n
        if x["id_libro"]:
            add_ejemplares(x["id_libro"], n)
        else:
            pendientes.append({"id_detalle": id_detalle, "descripcion": x["descripcion"], "cantidad_recibida": n})
    completa = all(x["cantidad_recibida"] >= x["cantidad"] for x in detalles.values())
    model.registrar_factura(id_solicitud, data["factura_folio"], data["factura_total"], completa, recepcion)
    notificaciones.enviar("tesoreria", f"Factura {data['factura_folio']}",
                          f"Solicitud {s['folio']}: factura {data['factura_folio']} por ${data['factura_total']} USD.",
                          actor["id_usuario"], "Tesorería")
    out = model.get(id_solicitud)
    out["pendientes_catalogar"] = pendientes
    return out
