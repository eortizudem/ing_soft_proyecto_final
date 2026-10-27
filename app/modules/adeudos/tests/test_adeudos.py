from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core import circulacion
from app.testing import make_book, make_loan, make_user, sql, uniq


def _loan(vencido_dias=0, **book):
    u = make_user()
    b = make_book(precio_referencia=100, **book)
    pid = make_loan(u["id_usuario"], b["id_libro"])
    if vencido_dias:
        sql("UPDATE prestamo SET fecha_vencimiento=%s WHERE id_prestamo=%s",
            (date.today() - timedelta(days=vencido_dias), pid))
    return u, b, pid


def _adeudo(u, tipo="retraso", monto=20):
    pid = sql("SELECT id_prestamo FROM prestamo WHERE id_usuario=%s LIMIT 1", (u["id_usuario"],))[0]["id_prestamo"]
    return sql("INSERT INTO adeudo(id_prestamo,tipo,monto) VALUES (%s,%s,%s) RETURNING id_adeudo",
               (pid, tipo, monto))[0]["id_adeudo"]


def _notifs(canal):
    return sql("SELECT count(*) AS n FROM bitacora WHERE accion=%s", (f"notif_{canal}",))[0]["n"]


def _compra(id_libro, precio):
    adm = sql("SELECT id_usuario FROM usuario WHERE matricula='ADM001'")[0]["id_usuario"]
    s = sql("INSERT INTO solicitud_compra(folio,id_usuario,justificacion,estado,fecha_recepcion) "
            "VALUES (%s,%s,'prueba','recibida',CURRENT_DATE) RETURNING id_solicitud", (f"Z{uniq(8)}", adm))[0]
    sql("INSERT INTO detalle_solicitud(id_solicitud,id_libro,descripcion,cantidad,precio_unitario) "
        "VALUES (%s,%s,'x',1,%s)", (s["id_solicitud"], id_libro, precio))


def test_permisos(alumno, anon):
    assert anon.get("/api/adeudos").status_code == 401
    assert alumno.get("/api/adeudos").status_code == 403
    assert alumno.get("/api/tipo-cambio").status_code == 403
    assert alumno.post("/api/adeudos/perdida", json={"id_prestamo": 1}).status_code == 403


def test_listar_y_filtros(bibliotecario):
    u, _, _ = _loan()
    id_ad = _adeudo(u)
    rows = bibliotecario.get(f"/api/adeudos?matricula={u['matricula']}").get_json()
    assert [r["id_adeudo"] for r in rows] == [id_ad]
    r = rows[0]
    assert r["usuario"]["matricula"] == u["matricula"] and r["libro"]["titulo"] and r["estado"] == "pendiente"
    assert bibliotecario.get(f"/api/adeudos?q={u['matricula']}&estado=pagado").get_json() == []
    assert len(bibliotecario.get(f"/api/adeudos?q={u['matricula']}&tipo=retraso&estado=pendiente").get_json()) == 1
    assert bibliotecario.get(f"/api/adeudos/{id_ad}").get_json()["id_adeudo"] == id_ad
    assert bibliotecario.get("/api/adeudos/99999999").status_code == 404


def test_pago(bibliotecario):
    u, _, _ = _loan()
    id_ad = _adeudo(u)
    assert bibliotecario.post(f"/api/adeudos/{id_ad}/pago", json={}).status_code == 400
    assert bibliotecario.post(f"/api/adeudos/{id_ad}/pago", json={"referencia_tesoreria": "ab"}).status_code == 400
    assert bibliotecario.post(f"/api/adeudos/{id_ad}/pago",
                              json={"referencia_tesoreria": "REF-1", "fecha_pago": "2999-01-01"}).status_code == 400
    r = bibliotecario.post(f"/api/adeudos/{id_ad}/pago", json={"referencia_tesoreria": "TES-2026-001"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["estado"] == "pagado" and d["fecha_pago"] == date.today().isoformat()
    assert bibliotecario.get(f"/api/adeudos/{id_ad}").get_json()["referencia_tesoreria"] == "TES-2026-001"
    assert sql("SELECT 1 FROM bitacora WHERE accion='adeudo_pago' AND detalle=%s",
               (f"adeudo {id_ad}: ref TES-2026-001",))
    assert sql("SELECT 1 FROM bitacora WHERE accion='notif_email' AND detalle LIKE %s", (f"{u['correo']}|%",))
    again = bibliotecario.post(f"/api/adeudos/{id_ad}/pago", json={"referencia_tesoreria": "TES-2026-002"})
    assert again.status_code == 409


def test_cancelar_solo_admin(admin, bibliotecario):
    u, _, _ = _loan()
    id_ad = _adeudo(u)
    assert bibliotecario.post(f"/api/adeudos/{id_ad}/cancelar", json={"motivo": "Caso especial"}).status_code == 403
    assert admin.post(f"/api/adeudos/{id_ad}/cancelar", json={"motivo": "no"}).status_code == 400
    r = admin.post(f"/api/adeudos/{id_ad}/cancelar", json={"motivo": "Caso especial"})
    assert r.status_code == 200 and r.get_json()["estado"] == "cancelado"
    assert admin.get(f"/api/adeudos/{id_ad}").get_json()["motivo_cancelacion"] == "Caso especial"
    assert sql("SELECT 1 FROM bitacora WHERE accion='adeudo_cancelar' AND detalle=%s", (f"adeudo {id_ad}: Caso especial",))
    assert admin.post(f"/api/adeudos/{id_ad}/cancelar", json={"motivo": "Otra vez"}).status_code == 409
    assert admin.post(f"/api/adeudos/{id_ad}/pago", json={"referencia_tesoreria": "REF-9"}).status_code == 409


def test_tipo_cambio(bibliotecario):
    r = bibliotecario.get("/api/tipo-cambio").get_json()
    assert r["usd_mxn"] == 18.0 and r["fuente"] == "simulado" and r["nota"]


def test_reposicion_con_y_sin_compra(bibliotecario):
    b = make_book(precio_referencia=33.33)
    r = bibliotecario.get(f"/api/adeudos/reposicion?id_libro={b['id_libro']}").get_json()
    assert (r["fuente"], r["valor_usd"], r["tipo_cambio"], r["monto_mxn"]) == ("precio_referencia", 33.33, 18.0, 599.94)
    _compra(b["id_libro"], 42)
    r = bibliotecario.get(f"/api/adeudos/reposicion?id_libro={b['id_libro']}").get_json()
    assert (r["fuente"], r["valor_usd"], r["monto_mxn"]) == ("ultima_compra", 42.0, 756.0)
    r = bibliotecario.get(f"/api/adeudos/reposicion?id_libro={b['id_libro']}&tipo_cambio=17.3333").get_json()
    assert r["monto_mxn"] == float(circulacion.valor_reposicion_mxn(42, "17.3333")) == 728.0
    assert bibliotecario.get("/api/adeudos/reposicion").status_code == 400
    assert bibliotecario.get("/api/adeudos/reposicion?id_libro=99999999").status_code == 404
    assert bibliotecario.get(f"/api/adeudos/reposicion?id_libro={b['id_libro']}&tipo_cambio=x").status_code == 400


def test_perdida(bibliotecario, app):
    u, b, pid = _loan(vencido_dias=7)
    se, te = _notifs("servicios_escolares"), _notifs("tesoreria")
    r = bibliotecario.post("/api/adeudos/perdida", json={"id_prestamo": pid, "tipo_cambio": 20.5})
    assert r.status_code == 201, r.get_json()
    d = r.get_json()
    assert d["valor_usd"] == 100.0 and d["tipo_cambio"] == 20.5 and d["monto_mxn"] == 2050.0
    tipos = {a["tipo"]: a for a in d["adeudos"]}
    assert tipos["perdida"]["monto"] == 2050.0 and tipos["perdida"]["estado"] == "pendiente"
    assert tipos["retraso"]["monto"] > 0 and tipos["retraso"]["dias_retraso"] > 0
    ej = sql("SELECT estado, motivo_baja FROM ejemplar WHERE id_ejemplar=(SELECT id_ejemplar FROM prestamo WHERE id_prestamo=%s)", (pid,))[0]
    assert (ej["estado"], ej["motivo_baja"]) == ("baja", "perdido")
    p = sql("SELECT estado, fecha_devolucion FROM prestamo WHERE id_prestamo=%s", (pid,))[0]
    assert p["estado"] == "devuelto" and p["fecha_devolucion"]
    assert (_notifs("servicios_escolares"), _notifs("tesoreria")) == (se + 1, te + 1)
    assert sql("SELECT 1 FROM bitacora WHERE accion='adeudo_perdida' AND detalle LIKE %s", (f"prestamo {pid}:%",))
    assert bibliotecario.post("/api/adeudos/perdida", json={"id_prestamo": pid}).status_code == 409
    # el usuario con adeudo pendiente no es autorizable; tras pagar todo, si
    with app.app_context():
        b2 = make_book()
        assert not circulacion.autorizar_prestamo(u["id_usuario"], b2["id_libro"])["autorizado"]
        for a in d["adeudos"]:
            assert bibliotecario.post(f"/api/adeudos/{a['id_adeudo']}/pago",
                                      json={"referencia_tesoreria": "REF-OK"}).status_code == 200
        assert circulacion.autorizar_prestamo(u["id_usuario"], b2["id_libro"])["autorizado"]


def test_perdida_sin_retraso_y_errores(bibliotecario):
    u, b, pid = _loan()
    assert bibliotecario.post("/api/adeudos/perdida", json={}).status_code == 400
    assert bibliotecario.post("/api/adeudos/perdida", json={"id_prestamo": 99999999}).status_code == 404
    assert bibliotecario.post("/api/adeudos/perdida", json={"id_prestamo": pid, "tipo_cambio": 0}).status_code == 400
    d = bibliotecario.post("/api/adeudos/perdida", json={"id_prestamo": pid}).get_json()
    assert [a["tipo"] for a in d["adeudos"]] == ["perdida"]
    assert Decimal(str(d["monto_mxn"])) == Decimal("1800.00")


@pytest.mark.parametrize("porc,monto", [(None, 900.0), (100, 1800.0), (10, 180.0)])
def test_danio(bibliotecario, porc, monto):
    u, b, pid = _loan()
    payload = {"id_prestamo": pid, **({"porcentaje": porc} if porc else {})}
    r = bibliotecario.post("/api/adeudos/danio", json=payload)
    assert r.status_code == 201, r.get_json()
    d = r.get_json()
    assert d["adeudo"]["tipo"] == "danio" and d["adeudo"]["monto"] == monto
    assert d["devolucion"]["ejemplar_estado"] == "disponible" and d["devolucion"]["adeudo_retraso"] is None
    assert sql("SELECT estado FROM ejemplar WHERE id_ejemplar=(SELECT id_ejemplar FROM prestamo WHERE id_prestamo=%s)",
               (pid,))[0]["estado"] == "disponible"
    assert bibliotecario.post("/api/adeudos/danio", json=payload).status_code == 409


def test_danio_baja_retraso_y_porcentaje_invalido(bibliotecario):
    u, b, pid = _loan(vencido_dias=7)
    assert bibliotecario.post("/api/adeudos/danio", json={"id_prestamo": pid, "porcentaje": 5}).status_code == 400
    assert bibliotecario.post("/api/adeudos/danio", json={"id_prestamo": pid, "porcentaje": 101}).status_code == 400
    d = bibliotecario.post("/api/adeudos/danio", json={"id_prestamo": pid, "dar_baja": True}).get_json()
    assert d["devolucion"]["ejemplar_estado"] == "baja" and d["devolucion"]["adeudo_retraso"]["monto"] > 0
    ej = sql("SELECT estado, motivo_baja FROM ejemplar WHERE id_ejemplar=(SELECT id_ejemplar FROM prestamo WHERE id_prestamo=%s)", (pid,))[0]
    assert (ej["estado"], ej["motivo_baja"]) == ("baja", "danado")


def test_danio_sin_baja_avisa_a_la_lista_de_espera(bibliotecario):
    u, b, pid = _loan(ejemplares=1)
    esperando = make_user()
    sql("INSERT INTO lista_espera(id_usuario,id_libro,posicion) VALUES (%s,%s,1)", (esperando["id_usuario"], b["id_libro"]))
    d = bibliotecario.post("/api/adeudos/danio", json={"id_prestamo": pid}).get_json()
    assert d["espera_notificada"]["id_usuario"] == esperando["id_usuario"]
    est = sql("SELECT estado FROM lista_espera WHERE id_usuario=%s", (esperando["id_usuario"],))[0]["estado"]
    assert est == "notificado"


def test_previsualizar(bibliotecario):
    u, b, pid = _loan(vencido_dias=7)
    r = bibliotecario.get(f"/api/adeudos/prestamo/{pid}?porcentaje=20&tipo_cambio=10").get_json()
    assert r["reposicion"]["monto_mxn"] == 1000.0 and r["monto_danio"] == 200.0 and r["abierto"]
    assert r["dias_retraso"] > 0 and r["monto_retraso"] == r["dias_retraso"] * 10
    assert bibliotecario.get(f"/api/adeudos/prestamo/{pid}?porcentaje=5").status_code == 400
    assert bibliotecario.get("/api/adeudos/prestamo/99999999").status_code == 404
