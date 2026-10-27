from app.testing import make_book, make_loan, make_user, sql

GLOBAL = {"usuarios_activos", "titulos_activos", "compras_pendientes", "prestamos_activos", "prestamos_vencidos",
          "adeudos_pendientes", "espera_activa", "consultas_pendientes"}


def test_stats(admin, anon):
    assert anon.get("/api/stats").status_code == 401
    j = admin.get("/api/stats").get_json()
    assert GLOBAL <= set(j) and {"mio", "presupuesto_mensual_usd", "presupuesto_usado_usd"} <= set(j)
    assert j["usuarios_activos"] >= 7 and j["titulos_activos"] >= 6 and j["prestamos_activos"] >= 4
    assert j["prestamos_vencidos"] >= 1 and j["adeudos_pendientes"] >= 20


def test_stats_personal_y_roles(bibliotecario, comprador, alumno):
    assert GLOBAL <= set(bibliotecario.get("/api/stats").get_json())
    assert "presupuesto_mensual_usd" in comprador.get("/api/stats").get_json()
    assert set(alumno.get("/api/stats").get_json()) == {"mio"}


def test_stats_vencidos_siguen_d24(admin):
    antes = admin.get("/api/stats").get_json()["prestamos_vencidos"]
    p = make_loan(make_user()["id_usuario"], make_book()["id_libro"])
    sql("UPDATE prestamo SET fecha_vencimiento=CURRENT_DATE-1 WHERE id_prestamo=%s", (p,))  # estado sigue 'activo'
    assert admin.get("/api/stats").get_json()["prestamos_vencidos"] == antes + 1


def test_estado_propio(app):
    from app.testing import client_as

    u = make_user()
    p = make_loan(u["id_usuario"], make_book()["id_libro"])
    sql("UPDATE prestamo SET fecha_vencimiento=CURRENT_DATE-3 WHERE id_prestamo=%s", (p,))
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',3,30)", (p,))
    mio = client_as(app, u["matricula"], u["password"]).get("/api/stats").get_json()["mio"]
    assert mio["prestamos_activos"] == 1 and mio["prestamos_vencidos"] == 1 and mio["adeudos_pendientes"] == 30
    assert mio["espera_activa"] == 0 and mio["proximo_vencimiento"]
