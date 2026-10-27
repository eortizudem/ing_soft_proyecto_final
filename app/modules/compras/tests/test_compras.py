import re
from decimal import Decimal

import pytest

from app.core import circulacion
from app.testing import make_book, sql


@pytest.fixture(autouse=True)
def presupuesto_amplio(app):
    """Las pruebas generales crean muchas solicitudes: presupuesto alto salvo en las pruebas de presupuesto."""
    previo = app.config.get("PRESUPUESTO_MENSUAL_USD")
    app.config["PRESUPUESTO_MENSUAL_USD"] = 10_000_000
    yield
    if previo is None:
        app.config.pop("PRESUPUESTO_MENSUAL_USD", None)
    else:
        app.config["PRESUPUESTO_MENSUAL_USD"] = previo


def _p(**over):
    d = {"justificacion": "Prueba de compra", "detalles": [
        {"descripcion": "Libro nuevo X", "cantidad": 2, "precio_unitario": 100.5},
        {"descripcion": "redes de COMPUTADORAS", "cantidad": 1, "precio_unitario": 800}]}
    d.update(over)
    return d


def test_permissions(alumno, anon):
    assert alumno.get("/api/compras").status_code == 403
    assert alumno.post("/api/compras", json=_p()).status_code == 403
    assert anon.get("/api/compras").status_code == 401


def test_seed_sol001(comprador):
    s = [x for x in comprador.get("/api/compras").get_json() if x["folio"] == "SOL001"][0]
    assert s["total_estimado"] == 2500 and s["estado"] == "pendiente" and len(s["detalles"]) == 2
    assert s["solicitante"] == "Responsable de compras" and s["fecha"] == "2026-10-14"


def test_total_folio_and_book_match(comprador):
    a = comprador.post("/api/compras", json=_p())
    assert a.status_code == 201
    a = a.get_json()
    assert a["total_estimado"] == 1001.0 and a["estado"] == "pendiente" and a["destinatario"] == "Tesorería"
    assert re.fullmatch(r"SOL\d{3,}", a["folio"])
    d = a["detalles"]
    assert d[0]["id_libro"] is None and d[0]["subtotal"] == 201.0
    assert d[1]["id_libro"] is not None
    b = comprador.post("/api/compras", json=_p(destinatario="Rectoría")).get_json()
    assert int(b["folio"][3:]) == int(a["folio"][3:]) + 1 and b["destinatario"] == "Rectoría"
    assert comprador.get(f"/api/compras/{b['id_solicitud']}").get_json()["folio"] == b["folio"]


def test_validation(comprador):
    line = {"descripcion": "X", "cantidad": 1, "precio_unitario": 1}
    for bad in ({"justificacion": ""}, {"detalles": []}, {"detalles": [{**line, "cantidad": 0}]},
                {"detalles": [{**line, "cantidad": 10001}]}, {"detalles": [{**line, "cantidad": 1.5}]},
                {"detalles": [{**line, "precio_unitario": -1}]}, {"detalles": [{**line, "precio_unitario": 10000001}]},
                {"detalles": [{**line, "descripcion": " "}]}):
        r = comprador.post("/api/compras", json=_p(**bad))
        assert r.status_code == 400 and r.get_json()["error"], bad


def test_enviar(comprador, admin):
    s = comprador.post("/api/compras", json=_p()).get_json()
    j = comprador.post(f"/api/compras/{s['id_solicitud']}/enviar").get_json()
    assert j["estado"] == "enviada"
    assert comprador.post(f"/api/compras/{s['id_solicitud']}/enviar").status_code == 400
    assert comprador.post("/api/compras/999999/enviar").status_code == 404
    acc = {r["accion"] for r in sql("SELECT accion FROM bitacora WHERE detalle LIKE %s", (f"%{s['folio']}%",))}
    assert {"compra_crear", "compra_enviar"} <= acc


def _enviada(c, detalles=None):
    s = c.post("/api/compras", json=_p(detalles=detalles) if detalles else _p()).get_json()
    return c.post(f"/api/compras/{s['id_solicitud']}/enviar").get_json()


def _rec(s, cantidades, folio="FAC-T-001", total=100):
    return {"factura_folio": folio, "factura_total": total,
            "lineas": [{"id_detalle": d["id_detalle"], "cantidad_recibida": n}
                       for d, n in zip(s["detalles"], cantidades)]}


def _presupuesto_holgura(c, app, holgura=1000):
    """Fija el presupuesto en (usado del mes + holgura) para tener un disponible conocido."""
    app.config["PRESUPUESTO_MENSUAL_USD"] = 0
    usado = c.get("/api/compras/presupuesto").get_json()["usado_usd"]
    app.config["PRESUPUESTO_MENSUAL_USD"] = usado + holgura


def test_presupuesto(comprador, app):
    _presupuesto_holgura(comprador, app)
    base = comprador.get("/api/compras/presupuesto").get_json()
    assert base["disponible_usd"] == 1000
    assert base["disponible_usd"] == base["presupuesto_usd"] - base["usado_usd"]
    assert comprador.get("/api/compras/presupuesto?mes=2020-01").get_json() == {
        "mes": "2020-01", "presupuesto_usd": base["presupuesto_usd"], "usado_usd": 0,
        "disponible_usd": base["presupuesto_usd"]}
    assert comprador.get("/api/compras/presupuesto?mes=xx").status_code == 400
    disp = base["disponible_usd"]
    line = {"descripcion": "Presupuesto X", "cantidad": 1, "precio_unitario": float(disp) + 1}
    r = comprador.post("/api/compras", json=_p(detalles=[line]))
    assert r.status_code == 422, r.get_json()
    assert r.get_json()["motivos"][0]["codigo"] == "PRESUPUESTO_EXCEDIDO"
    assert "USD " in r.get_json()["motivos"][0]["mensaje"]  # montos con formato USD uniforme
    ok = comprador.post("/api/compras", json=_p(detalles=[{**line, "precio_unitario": float(disp)}]))
    assert ok.status_code == 201
    assert comprador.get("/api/compras/presupuesto").get_json()["disponible_usd"] == 0


def test_cancelar_libera_presupuesto(comprador, app):
    _presupuesto_holgura(comprador, app)
    disp = comprador.get("/api/compras/presupuesto").get_json()["disponible_usd"]
    s = comprador.post("/api/compras", json=_p(detalles=[
        {"descripcion": "Cancelable", "cantidad": 1, "precio_unitario": float(disp)}])).get_json()
    c = comprador.post(f"/api/compras/{s['id_solicitud']}/cancelar").get_json()
    assert c["estado"] == "cancelada"
    assert comprador.get("/api/compras/presupuesto").get_json()["disponible_usd"] == disp
    assert comprador.post(f"/api/compras/{s['id_solicitud']}/cancelar").status_code == 409
    assert comprador.post("/api/compras/999999/cancelar").status_code == 404
    assert comprador.post(f"/api/compras/{s['id_solicitud']}/recibir", json={}).status_code == 409
    assert sql("SELECT 1 FROM bitacora WHERE accion='compra_cancelar' AND detalle LIKE %s", (f"%{s['folio']}%",))


def test_recepcion_requiere_enviada(comprador):
    s = comprador.post("/api/compras", json=_p()).get_json()
    r = comprador.post(f"/api/compras/{s['id_solicitud']}/recibir", json=_rec(s, [1, 1]))
    assert r.status_code == 409


def test_recepcion_parcial_y_total(comprador, alumno, app):
    libro = make_book()
    lineas = [{"descripcion": libro["titulo"], "cantidad": 3, "precio_unitario": 55},
              {"descripcion": "Titulo sin catalogar zz", "cantidad": 2, "precio_unitario": 10}]
    s = _enviada(comprador, lineas)
    assert s["detalles"][0]["id_libro"] == libro["id_libro"] and s["detalles"][0]["cantidad_recibida"] == 0
    url = f"/api/compras/{s['id_solicitud']}/recibir"
    n0 = sql("SELECT count(*) AS n FROM ejemplar WHERE id_libro=%s", (libro["id_libro"],))[0]["n"]
    assert alumno.post(url, json=_rec(s, [1, 0])).status_code == 403

    # validaciones
    assert comprador.post(url, json=_rec(s, [4, 0])).status_code == 400
    assert comprador.post(url, json=_rec(s, [0, 0])).status_code == 400
    assert comprador.post(url, json={**_rec(s, [1, 0]), "factura_folio": "AB"}).status_code == 400
    assert comprador.post(url, json={**_rec(s, [1, 0]), "factura_total": -1}).status_code == 400
    assert comprador.post(url, json={**_rec(s, [1, 0]), "lineas": [{"id_detalle": 1, "cantidad_recibida": 1}]}
                          ).status_code == 400

    # parcial: libro ligado suma ejemplares; la linea sin libro queda pendiente de catalogar
    r = comprador.post(url, json=_rec(s, [2, 1], folio="FAC-P-1", total=150)).get_json()
    assert r["estado"] == "enviada" and r["factura_folio"] == "FAC-P-1" and r["fecha_recepcion"] is None
    assert [d["cantidad_recibida"] for d in r["detalles"]] == [2, 1]
    assert r["pendientes_catalogar"] == [{"id_detalle": s["detalles"][1]["id_detalle"],
                                          "descripcion": "Titulo sin catalogar zz", "cantidad_recibida": 1}]
    assert sql("SELECT count(*) AS n FROM ejemplar WHERE id_libro=%s", (libro["id_libro"],))[0]["n"] == n0 + 2
    assert comprador.post(f"/api/compras/{s['id_solicitud']}/cancelar").status_code == 409
    assert comprador.post(url, json=_rec(s, [2, 0])).status_code == 400  # excede lo pedido (acumulado)

    # total
    r = comprador.post(url, json=_rec(s, [1, 1], folio="FAC-P-2", total=60)).get_json()
    assert r["estado"] == "recibida" and r["fecha_recepcion"] and r["factura_folio"] == "FAC-P-2"
    assert r["factura_total"] == 210
    assert sql("SELECT count(*) AS n FROM ejemplar WHERE id_libro=%s", (libro["id_libro"],))[0]["n"] == n0 + 3
    assert comprador.post(url, json=_rec(s, [1, 0])).status_code == 409

    # aviso a Tesoreria + bitacora
    avisos = sql("SELECT detalle FROM bitacora WHERE accion='notif_tesoreria' AND detalle LIKE %s",
                 (f"%{s['folio']}%",))
    assert len(avisos) == 2 and any("FAC-P-2" in a["detalle"] for a in avisos)
    assert sql("SELECT 1 FROM bitacora WHERE accion='compra_recibir' AND detalle LIKE %s", (f"%{s['folio']}%",))

    # la recepcion fija el precio de reposicion
    with app.app_context():
        v = circulacion.valor_reposicion(libro["id_libro"])
    assert v["fuente"] == "ultima_compra" and v["valor_usd"] == Decimal("55")
    assert comprador.get(f"/api/compras/{s['id_solicitud']}").get_json()["detalles"][0]["id_detalle"]
