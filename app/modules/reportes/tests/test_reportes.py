from datetime import date

from app.testing import sql, uniq


def _count():
    return sql("SELECT count(*) AS n FROM reporte_generado")[0]["n"]


def test_catalogo_report_logged(catalogo):
    n = _count()
    r = catalogo.get("/api/reportes/catalogo_activo?formato=pdf")
    assert r.status_code == 200
    j = r.get_json()
    assert j["tipo"] == "catalogo_activo" and j["total"] == len(j["filas"]) >= 6
    assert len(j["columnas"]) == len(j["filas"][0]) and j["generado_por"]
    assert _count() == n + 1
    last = sql("SELECT tipo, formato FROM reporte_generado ORDER BY id_reporte DESC LIMIT 1")[0]
    assert last == {"tipo": "catalogo_activo", "formato": "pdf"}
    assert sql("SELECT 1 FROM bitacora WHERE accion='reporte' LIMIT 1")


def test_usuarios_report_needs_usuarios_permission(catalogo, admin):
    assert catalogo.get("/api/reportes/usuarios").status_code == 403
    j = admin.get("/api/reportes/usuarios").get_json()
    assert j["columnas"][0] == "Matrícula" and j["total"] >= 7


def test_circulacion_reports_need_prestamos_permission(catalogo, bibliotecario):
    for tipo in ("con_adeudos", "prestamos_vencidos", "prestamos"):
        assert catalogo.get(f"/api/reportes/{tipo}").status_code == 403, tipo
        assert bibliotecario.get(f"/api/reportes/{tipo}").status_code == 200, tipo
    assert catalogo.get("/api/reportes/catalogo_completo").status_code == 200


def test_report_permissions_and_errors(alumno, comprador, admin):
    assert alumno.get("/api/reportes/catalogo_completo").status_code == 403
    assert comprador.get("/api/reportes/catalogo_completo").status_code == 403
    assert admin.get("/api/reportes/nada").status_code == 404
    assert admin.get("/api/reportes/catalogo_completo?formato=xx").status_code == 400
    n = _count()
    assert admin.get("/api/reportes/catalogo_completo").status_code == 200 and _count() == n + 1


# ---- RF-16, RF-28 y reportes de circulación ----
from app.core import circulacion  # noqa: E402
from app.testing import make_book, make_loan, make_user  # noqa: E402


def _vencer(id_prestamo, dias=10):
    sql("UPDATE prestamo SET fecha_vencimiento=CURRENT_DATE-%s WHERE id_prestamo=%s", (dias, id_prestamo))


def _adeudo(id_prestamo, monto=30):
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',3,%s)", (id_prestamo, monto))


def _con_adeudos(cli, extra=""):
    return {f[0]: f for f in cli.get("/api/reportes/con_adeudos" + extra).get_json()["filas"]}


def test_con_adeudos_cuatro_casos_y_definicion_d09(bibliotecario, app):
    libro = make_book(ejemplares=4)
    con_vencido, con_adeudo, ambos, limpio = (make_user() for _ in range(4))
    _vencer(make_loan(con_vencido["id_usuario"], libro["id_libro"]))
    p = make_loan(con_adeudo["id_usuario"], libro["id_libro"])
    sql("UPDATE prestamo SET estado='devuelto', fecha_devolucion=now() WHERE id_prestamo=%s", (p,))
    _adeudo(p, 20)
    p = make_loan(ambos["id_usuario"], libro["id_libro"])
    _vencer(p, 4)
    _adeudo(p, 45)
    make_loan(limpio["id_usuario"], libro["id_libro"])  # abierto pero vigente
    d = _con_adeudos(bibliotecario)
    assert con_vencido["matricula"] in d and con_adeudo["matricula"] in d and ambos["matricula"] in d
    assert limpio["matricula"] not in d
    fila = d[con_vencido["matricula"]]  # Matrícula, Nombre, Correo, vencidos, días, adeudo, suspendido
    assert fila[3] == 1 and fila[4] >= 5 and fila[5] == 0 and fila[6] == "Sí"
    assert d[con_adeudo["matricula"]][3] == 0 and d[con_adeudo["matricula"]][5] == 20
    assert d[ambos["matricula"]][3] == 1 and d[ambos["matricula"]][5] == 45
    # idéntico a contexto_usuario (D-09): deudor <=> suspendido
    with app.app_context():
        for u in (con_vencido, con_adeudo, ambos, limpio):
            assert circulacion.contexto_usuario(u["id_usuario"])["suspendido"] == (u["matricula"] in d)


def test_con_adeudos_docentes_opcionales(bibliotecario):
    doc = make_user(rol="docente")
    _vencer(make_loan(doc["id_usuario"], make_book()["id_libro"]))
    assert doc["matricula"] not in _con_adeudos(bibliotecario)
    assert doc["matricula"] in _con_adeudos(bibliotecario, "?incluir_docentes=1")


def test_aviso_servicios_escolares(bibliotecario, catalogo):
    u = make_user()
    _vencer(make_loan(u["id_usuario"], make_book()["id_libro"]))
    assert catalogo.post("/api/reportes/con_adeudos/aviso", json={}).status_code == 403
    r = bibliotecario.post("/api/reportes/con_adeudos/aviso", json={})
    j = r.get_json()
    assert r.status_code == 200 and u["matricula"] in j["matriculas"] and j["enviados"] == len(j["matriculas"])
    assert sql("SELECT 1 FROM bitacora WHERE accion='notif_servicios_escolares' AND detalle LIKE %s", ("Servicios Escolares|%",))
    assert sql("SELECT 1 FROM bitacora WHERE accion='reporte_con_adeudos_aviso'")


def test_aviso_sin_con_adeudos_422(bibliotecario, monkeypatch):
    from app.modules.reportes import model

    monkeypatch.setattr(model, "con_adeudos", lambda roles: [])
    n = sql("SELECT count(*) AS n FROM bitacora WHERE accion='notif_servicios_escolares'")[0]["n"]
    assert bibliotecario.post("/api/reportes/con_adeudos/aviso", json={}).status_code == 422
    assert sql("SELECT count(*) AS n FROM bitacora WHERE accion='notif_servicios_escolares'")[0]["n"] == n


def test_inventario_estante_filtros_y_bajas(catalogo, alumno):
    libro = make_book(ejemplares=3, planta="Planta Z", pasillo="Q", librero=7, tema="Astrofísica")
    make_loan(make_user()["id_usuario"], libro["id_libro"])
    sql("UPDATE ejemplar SET estado='baja', motivo_baja='perdido' WHERE id_libro=%s AND numero_copia=3", (libro["id_libro"],))
    assert alumno.get("/api/reportes/inventario_estante").status_code == 403
    r = catalogo.get("/api/reportes/inventario_estante?planta=Planta Z&pasillo=q&librero=7&tema=astrofisica")
    j = r.get_json()
    assert j["columnas"][-1] == "Conteo físico" and j["total"] == 1
    clave, _, ubic, exist, disp, prest, bajas, conteo = j["filas"][0]
    assert clave == libro["clave"] and "Planta Z" in ubic and (exist, disp, prest, bajas, conteo) == (2, 1, 1, 1, "")
    assert catalogo.get("/api/reportes/inventario_estante?planta=Inexistente").get_json()["total"] == 0
    assert catalogo.get("/api/reportes/inventario_estante?pasillo=ZZ").status_code == 400


def test_prestamos_vencidos_y_periodo(bibliotecario):
    u = make_user()
    p = make_loan(u["id_usuario"], make_book()["id_libro"])
    _vencer(p, 14)
    f = next(f for f in bibliotecario.get("/api/reportes/prestamos_vencidos").get_json()["filas"] if f[0] == u["matricula"])
    assert f[6] >= 9 and float(f[7]) == f[6] * 10  # días hábiles x $10 (política alumno)
    hoy = sql("SELECT CURRENT_DATE AS d")[0]["d"].isoformat()
    j = bibliotecario.get(f"/api/reportes/prestamos?desde={hoy}&hasta={hoy}").get_json()
    assert j["columnas"][-1] == "Estado" and any(f[0] == p and f[-1] == "vencido" for f in j["filas"])
    assert bibliotecario.get("/api/reportes/prestamos?desde=2000-01-01&hasta=2000-01-02").get_json()["total"] == 0
    assert bibliotecario.get("/api/reportes/prestamos?desde=xx").status_code == 400
    assert bibliotecario.get(f"/api/reportes/prestamos?desde={hoy}&hasta=2000-01-01").status_code == 400


def test_nuevos_tipos_quedan_registrados(admin):
    for tipo in ("con_adeudos", "inventario_estante", "prestamos_vencidos", "prestamos"):
        n = _count()
        assert admin.get(f"/api/reportes/{tipo}?formato=impresion").status_code == 200
        assert _count() == n + 1
        assert sql("SELECT tipo, formato FROM reporte_generado ORDER BY id_reporte DESC LIMIT 1")[0] == \
            {"tipo": tipo, "formato": "impresion"}


# ---- Indicadores (PS-MET-02/03, CTX-03) e errores (PS-S3-06) ----
def _indicadores(cli, extra=""):
    j = cli.get("/api/reportes/indicadores" + extra).get_json()
    assert j["columnas"] == ["Área", "Indicador", "Valor", "Detalle"]
    return {(f[0], f[1]): f[2] for f in j["filas"]}


def test_indicadores_discrepancias_de_inventario(bibliotecario):
    base = _indicadores(bibliotecario)
    libro = make_book(ejemplares=2)
    u = make_user()
    make_loan(u["id_usuario"], libro["id_libro"])                       # consistente: no suma discrepancias
    sql("UPDATE ejemplar SET estado='prestado' WHERE id_libro=%s AND numero_copia=2", (libro["id_libro"],))   # sin prestamo
    sin_ejemplares = make_book(ejemplares=0)
    m = _indicadores(bibliotecario)
    assert m[("Inventario", "Ejemplares «prestado» sin préstamo abierto")] == \
        base[("Inventario", "Ejemplares «prestado» sin préstamo abierto")] + 1
    assert m[("Inventario", "Libros activos sin ejemplares")] == base[("Inventario", "Libros activos sin ejemplares")] + 1
    sql("UPDATE ejemplar SET estado='disponible' WHERE id_libro=%s AND numero_copia=1", (libro["id_libro"],))  # con prestamo
    m = _indicadores(bibliotecario)
    assert m[("Inventario", "Ejemplares «disponible» con préstamo abierto")] == \
        base[("Inventario", "Ejemplares «disponible» con préstamo abierto")] + 1
    assert sin_ejemplares["id_libro"]


def test_indicadores_asistente_y_periodos(bibliotecario, alumno):
    antes = _indicadores(bibliotecario)
    alumno.post("/api/asistente/mensajes", json={"texto": "quiero hablar con un bibliotecario", "canal": "web"})
    despues = _indicadores(bibliotecario)
    assert despues[("Asistente", "Conversaciones totales")] == antes[("Asistente", "Conversaciones totales")] + 1
    assert despues[("Asistente", "Consultas para el bibliotecario pendientes")] == antes[("Asistente", "Consultas para el bibliotecario pendientes")] + 1
    assert despues[("Circulación", "Tiempo de atención de préstamo/devolución")] == "No disponible"
    assert str(despues[("Asistente", "Atendidas sin pasar a bibliotecario")]).endswith(" %")
    mes = date.today().strftime("%Y-%m")
    assert ("Préstamos por periodo", mes) in despues
    vacio = _indicadores(bibliotecario, "?desde=2000-01-01&hasta=2000-01-31")
    assert not [k for k in vacio if k[0] == "Préstamos por periodo"]


def test_indicadores_sin_permiso_reportes(alumno, comprador):
    assert alumno.get("/api/reportes/indicadores").status_code == 403
    assert comprador.get("/api/reportes/errores").status_code == 403


def test_reporte_de_errores(admin, anon):
    from app.core import errores
    errores.reiniciar_limites()
    marca = "falla-" + uniq()
    anon.post("/api/errores", json={"mensaje": marca, "ruta": "/inicio", "origen": "app.js:3"})
    j = admin.get("/api/reportes/errores").get_json()
    assert j["columnas"] == ["Fecha", "Origen", "Usuario", "Detalle"]
    fila = next(f for f in j["filas"] if marca in f[3])
    assert fila[1:3] == ["cliente", "Sin sesión"] and fila[3].startswith("/inicio: ")
    assert admin.get("/api/reportes/errores?desde=2000-01-01&hasta=2000-01-02").get_json()["total"] == 0
    assert sql("SELECT 1 FROM reporte_generado WHERE tipo='errores' LIMIT 1")
