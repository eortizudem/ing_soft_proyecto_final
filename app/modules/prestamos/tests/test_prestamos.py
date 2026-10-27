import threading
from datetime import date, timedelta

import pytest

from app.core import calendario, circulacion
from app.modules.prestamos import service
from app.testing import client_as, make_book, make_loan, make_user, sql


# ------------------------------------------------------------------ helpers
def _validar(c, usuario, libro, **extra):
    r = c.post("/api/prestamos/validar", json={"matricula": usuario["matricula"], "clave": libro["clave"], **extra})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _codigos(r):
    return {m["codigo"] for m in r["motivos"]}


def _prestar(c, usuario, libro, **extra):
    return c.post("/api/prestamos", json={"matricula": usuario["matricula"], "clave": libro["clave"], **extra})


def _loan_for(usuario, ejemplares=1, **book):
    libro = make_book(ejemplares=ejemplares, **book)
    return libro, make_loan(usuario["id_usuario"], libro["id_libro"])


def _cerrar(id_prestamo):
    sql("UPDATE ejemplar SET estado='disponible' WHERE id_ejemplar=(SELECT id_ejemplar FROM prestamo WHERE id_prestamo=%s)",
        (id_prestamo,))
    sql("UPDATE prestamo SET fecha_devolucion=now(), estado='devuelto' WHERE id_prestamo=%s", (id_prestamo,))


def _vence(id_prestamo, fecha):
    sql("UPDATE prestamo SET fecha_vencimiento=%s WHERE id_prestamo=%s", (fecha, id_prestamo))


def _bitacora(accion, like="%"):
    return sql("SELECT detalle FROM bitacora WHERE accion=%s AND detalle LIKE %s", (accion, like))


def _fake_today(monkeypatch, dia):
    class Fake(date):
        @classmethod
        def today(cls):
            return dia

    monkeypatch.setattr(service, "date", Fake)


# ------------------------------------------------------------------ permisos
def test_permisos(alumno, anon, colaborador, bibliotecario):
    for ruta in ("/api/prestamos", "/api/politicas"):
        assert anon.get(ruta).status_code == 401
        assert alumno.get(ruta).status_code == 403
        assert colaborador.get(ruta).status_code == 403
    assert alumno.post("/api/prestamos", json={}).status_code == 403
    assert anon.post("/api/prestamos/validar", json={}).status_code == 401
    assert bibliotecario.get("/api/prestamos").status_code == 200
    assert bibliotecario.get("/api/politicas").status_code == 200


# ------------------------------------------------------------------ RN-01 una por una
def test_validar_autorizado(bibliotecario):
    u, libro = make_user(), make_book()
    r = _validar(bibliotecario, u, libro)
    assert r["autorizado"] and r["motivos"] == []
    assert r["usuario"]["max_libros"] == 2 and r["usuario"]["prestamos_activos"] == 0
    assert r["libro"]["disponibles"] == 3 and r["dias_prestamo"] == 5
    assert r["fecha_vencimiento_estimada"] == circulacion.fecha_vencimiento(date.today(), 5).isoformat()
    por_id = bibliotecario.post("/api/prestamos/validar", json={"matricula": u["matricula"].lower(), "id_libro": libro["id_libro"]})
    assert por_id.get_json()["autorizado"]


def test_validar_usuario_y_libro_inexistentes(bibliotecario):
    u, libro = make_user(), make_book()
    r = bibliotecario.post("/api/prestamos/validar", json={"matricula": "NOEXISTE9", "clave": libro["clave"]}).get_json()
    assert not r["autorizado"] and "USUARIO_NO_ENCONTRADO" in _codigos(r)
    r = bibliotecario.post("/api/prestamos/validar", json={"matricula": u["matricula"], "clave": "NOLIBRO"}).get_json()
    assert not r["autorizado"] and "LIBRO_NO_ENCONTRADO" in _codigos(r)
    assert bibliotecario.post("/api/prestamos/validar", json={"matricula": u["matricula"]}).status_code == 400
    assert bibliotecario.post("/api/prestamos/validar", json={"clave": "X"}).status_code == 400


def test_alumno_con_dos_prestamos_rechazado(bibliotecario):
    u = make_user()
    _loan_for(u)
    assert _validar(bibliotecario, u, make_book())["autorizado"]  # con 1 aun puede
    _loan_for(u)
    r = _validar(bibliotecario, u, make_book())
    assert not r["autorizado"] and _codigos(r) == {"LIMITE_EJEMPLARES"}


def test_docente_con_tres_prestamos_rechazado(bibliotecario):
    d = make_user(rol="docente")
    for _ in range(2):
        _loan_for(d)
    r = _validar(bibliotecario, d, make_book())
    assert r["autorizado"] and r["dias_prestamo"] == 10 and r["usuario"]["max_libros"] == 3
    _loan_for(d)
    assert _codigos(_validar(bibliotecario, d, make_book())) == {"LIMITE_EJEMPLARES"}


def test_con_multa_pendiente(bibliotecario):
    u = make_user()
    _, pid = _loan_for(u)
    _cerrar(pid)
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',1,10)", (pid,))
    assert _codigos(_validar(bibliotecario, u, make_book())) == {"MULTAS_PENDIENTES"}


def test_con_prestamo_vencido(bibliotecario):
    u = make_user()
    _, pid = _loan_for(u)
    _vence(pid, date.today() - timedelta(days=3))
    assert _codigos(_validar(bibliotecario, u, make_book())) == {"PRESTAMOS_VENCIDOS"}


@pytest.mark.parametrize("tipo,codigo", [("consulta_interna", "LIBRO_NO_PRESTABLE"), ("reservado", "LIBRO_NO_PRESTABLE"),
                                         ("prestamo_externo", "LIBRO_NO_DISPONIBLE")])
def test_libro_no_prestable_o_sin_copias(bibliotecario, tipo, codigo):
    u = make_user()
    libro = make_book(tipo_uso=tipo, ejemplares=0 if codigo == "LIBRO_NO_DISPONIBLE" else 2)
    assert _codigos(_validar(bibliotecario, u, libro)) == {codigo}


def test_libro_inactivo_y_usuario_inactivo(bibliotecario):
    assert "LIBRO_INACTIVO" in _codigos(_validar(bibliotecario, make_user(), make_book(estado="inactivo")))
    assert "USUARIO_INACTIVO" in _codigos(_validar(bibliotecario, make_user(estado="inactivo"), make_book()))


def test_sin_politica_activa(bibliotecario):
    assert "SIN_POLITICA" in _codigos(_validar(bibliotecario, make_user(rol="comprador"), make_book()))


def test_reservado_para_otro_usuario(bibliotecario):
    esperando, otro = make_user(), make_user()
    libro = make_book(ejemplares=1)
    sql("INSERT INTO lista_espera(id_usuario,id_libro,estado,fecha_notificacion,fecha_limite_recoger) "
        "VALUES (%s,%s,'notificado',now(),now()+interval '2 days')", (esperando["id_usuario"], libro["id_libro"]))
    assert _codigos(_validar(bibliotecario, otro, libro)) == {"LIBRO_RESERVADO_OTRO_USUARIO"}
    assert _validar(bibliotecario, esperando, libro)["autorizado"]


# ------------------------------------------------------------------ vigencia (RN-05/06, D-03)
@pytest.mark.parametrize("dia,dias,esperado", [
    (date(2026, 10, 30), 5, date(2026, 11, 6)),    # viernes: el lunes es el dia 1
    (date(2026, 10, 31), 5, date(2026, 11, 6)),    # sabado: se cuenta desde el lunes
    (date(2026, 10, 30), 10, date(2026, 11, 13)),
    (date(2026, 10, 31), 10, date(2026, 11, 13)),
    (date(2026, 10, 26), 5, date(2026, 11, 2)),    # lunes -> lunes siguiente (el dia de prestamo no cuenta)
])
def test_vigencia_5_y_10_habiles(dia, dias, esperado):
    assert circulacion.fecha_vencimiento(dia, dias) == esperado


def test_vigencia_en_prestamo_real(bibliotecario):
    for rol, dias in (("alumno", 5), ("docente", 10)):
        u, libro = make_user(rol=rol), make_book()
        p = _prestar(bibliotecario, u, libro).get_json()["prestamo"]
        assert p["fecha_vencimiento"] == calendario.sumar_habiles(date.today(), dias).isoformat()


# ------------------------------------------------------------------ crear + recibo
def test_crear_prestamo_y_recibo(bibliotecario):
    u, libro = make_user(), make_book(ejemplares=1)
    r = _prestar(bibliotecario, u, libro)
    assert r.status_code == 201, r.get_json()
    d = r.get_json()
    p, rec = d["prestamo"], d["recibo"]
    assert p["estado"] == "activo" and p["usuario"]["matricula"] == u["matricula"] and p["libro"]["clave"] == libro["clave"]
    assert p["num_renovaciones"] == 0 and p["max_renovaciones"] == 2 and p["dias_retraso"] == 0
    assert sql("SELECT estado FROM ejemplar WHERE id_ejemplar=%s", (p["id_ejemplar"],))[0]["estado"] == "prestado"
    assert rec["folio"] == f"REC-{p['id_prestamo']:06d}" and rec["libro"]["ubicacion"]["planta"] == "Planta baja"
    assert rec["dias_prestamo"] == 5 and rec["politica"] == {"max_renovaciones": 2, "multa_diaria": 10.0}
    assert [n["canal"] for n in rec["notificaciones"]] == ["email"]
    assert _bitacora("notif_email", f"{u['correo']}|Recibo de préstamo {rec['folio']}%")
    assert _bitacora("prestamo_crear", f"{p['folio']}%")
    # sin copias: 422 con motivos
    r2 = _prestar(bibliotecario, make_user(), libro)
    assert r2.status_code == 422 and r2.get_json()["motivos"][0]["codigo"] == "LIBRO_NO_DISPONIBLE"
    assert _validar(bibliotecario, make_user(), libro)["libro"]["disponibles"] == 0  # disponibilidad inmediata


def test_crear_422_conserva_codigos_y_no_escribe(bibliotecario):
    u = make_user(estado="inactivo")
    libro = make_book()
    r = _prestar(bibliotecario, u, libro)
    assert r.status_code == 422 and "USUARIO_INACTIVO" in {m["codigo"] for m in r.get_json()["motivos"]}
    assert sql("SELECT count(*) AS n FROM ejemplar WHERE id_libro=%s AND estado='disponible'", (libro["id_libro"],))[0]["n"] == 3
    r = _prestar(bibliotecario, make_user(), {"clave": "NOLIBRO"})
    assert r.status_code == 422 and r.get_json()["motivos"][0]["codigo"] == "LIBRO_NO_ENCONTRADO"


def test_canales_del_recibo(bibliotecario):
    u, libro = make_user(), make_book()
    d = _prestar(bibliotecario, u, libro, canales=["email", "whatsapp"]).get_json()
    assert [n["canal"] for n in d["recibo"]["notificaciones"]] == ["email", "whatsapp"]
    assert _prestar(bibliotecario, make_user(), libro, canales=["fax"]).status_code == 400
    assert _prestar(bibliotecario, make_user(), libro, canales=["tesoreria"]).status_code == 400
    pid = d["prestamo"]["id_prestamo"]
    r = bibliotecario.post(f"/api/prestamos/{pid}/recibo/enviar", json={"canales": ["whatsapp"]})
    assert r.status_code == 200 and r.get_json() == {"enviados": ["whatsapp"]}
    assert len(bibliotecario.get(f"/api/prestamos/{pid}/recibo").get_json()["notificaciones"]) == 3
    assert bibliotecario.post(f"/api/prestamos/{pid}/recibo/enviar", json={"canales": []}).status_code == 400
    assert bibliotecario.post("/api/prestamos/999999/recibo/enviar", json={"canales": ["email"]}).status_code == 404
    assert bibliotecario.get("/api/prestamos/999999/recibo").status_code == 404


def test_recoger_espera_al_prestar(bibliotecario):
    u, libro = make_user(), make_book(ejemplares=1)
    sql("INSERT INTO lista_espera(id_usuario,id_libro,estado,fecha_notificacion,fecha_limite_recoger) "
        "VALUES (%s,%s,'notificado',now(),now()+interval '2 days')", (u["id_usuario"], libro["id_libro"]))
    assert _prestar(bibliotecario, u, libro).status_code == 201
    assert sql("SELECT estado FROM lista_espera WHERE id_usuario=%s AND id_libro=%s",
               (u["id_usuario"], libro["id_libro"]))[0]["estado"] == "recogido"


def test_concurrencia_ultimo_ejemplar(app):
    libro = make_book(ejemplares=1)
    usuarios = [make_user(), make_user()]
    clientes = [client_as(app, "BIB001", "Biblioteca123") for _ in usuarios]
    barrera, estados = threading.Barrier(2), []

    def intentar(c, u):
        barrera.wait()
        estados.append(_prestar(c, u, libro).status_code)

    hilos = [threading.Thread(target=intentar, args=(c, u)) for c, u in zip(clientes, usuarios)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert sorted(estados) == [201, 422]
    assert sql("SELECT count(*) AS n FROM prestamo p JOIN ejemplar e USING (id_ejemplar) WHERE e.id_libro=%s",
               (libro["id_libro"],))[0]["n"] == 1


# ------------------------------------------------------------------ renovar
def test_renovaciones_alumno_2_y_docente_3(bibliotecario):
    for rol, maximo, dias in (("alumno", 2, 5), ("docente", 3, 10)):
        u = make_user(rol=rol)
        pid = _prestar(bibliotecario, u, make_book()).get_json()["prestamo"]["id_prestamo"]
        venc = date.fromisoformat(bibliotecario.get(f"/api/prestamos/{pid}").get_json()["fecha_vencimiento"])
        for n in range(1, maximo + 1):
            r = bibliotecario.post(f"/api/prestamos/{pid}/renovar")
            assert r.status_code == 200, r.get_json()
            venc = circulacion.fecha_renovacion(venc, dias)
            assert r.get_json()["renovacion"]["nueva_fecha_vencimiento"] == venc.isoformat()
            assert r.get_json()["prestamo"]["num_renovaciones"] == n
        r = bibliotecario.post(f"/api/prestamos/{pid}/renovar")
        assert r.status_code == 422 and r.get_json()["motivos"][0]["codigo"] == "MAX_RENOVACIONES"
        d = bibliotecario.get(f"/api/prestamos/{pid}").get_json()
        assert len(d["renovaciones"]) == maximo and d["renovaciones"][-1]["nueva_fecha_vencimiento"] == venc.isoformat()
        assert _bitacora("prestamo_renovar", f"{d['folio']}%")


def test_renovar_rechazos_d05(bibliotecario):
    u = make_user()
    libro, pid = _loan_for(u)
    # vencido
    _vence(pid, date.today() - timedelta(days=2))
    r = bibliotecario.post(f"/api/prestamos/{pid}/renovar")
    assert r.status_code == 422 and "PRESTAMO_VENCIDO" in {m["codigo"] for m in r.get_json()["motivos"]}
    _vence(pid, date.today() + timedelta(days=2))
    # lista de espera activa
    otro = make_user()
    sql("INSERT INTO lista_espera(id_usuario,id_libro) VALUES (%s,%s)", (otro["id_usuario"], libro["id_libro"]))
    r = bibliotecario.post(f"/api/prestamos/{pid}/renovar")
    assert r.status_code == 422 and {m["codigo"] for m in r.get_json()["motivos"]} == {"LISTA_ESPERA"}
    sql("UPDATE lista_espera SET estado='cancelado' WHERE id_usuario=%s", (otro["id_usuario"],))
    # adeudos pendientes (de otro prestamo cerrado)
    _, previo = _loan_for(u)
    _cerrar(previo)
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',1,10)", (previo,))
    r = bibliotecario.post(f"/api/prestamos/{pid}/renovar")
    assert r.status_code == 422 and {m["codigo"] for m in r.get_json()["motivos"]} == {"MULTAS_PENDIENTES"}
    sql("UPDATE adeudo SET estado='pagado' WHERE id_prestamo=%s", (previo,))
    assert bibliotecario.post(f"/api/prestamos/{pid}/renovar").status_code == 200
    # cerrado
    _cerrar(pid)
    r = bibliotecario.post(f"/api/prestamos/{pid}/renovar")
    assert r.status_code == 422 and r.get_json()["motivos"][0]["codigo"] == "PRESTAMO_CERRADO"
    assert bibliotecario.post("/api/prestamos/999999/renovar").status_code == 404


# ------------------------------------------------------------------ devolver
def _devolver_con_hoy(monkeypatch, c, hoy, vencimiento):
    u, libro = make_user(), make_book(ejemplares=1)
    pid = _prestar(c, u, libro).get_json()["prestamo"]["id_prestamo"]
    _vence(pid, vencimiento)
    _fake_today(monkeypatch, hoy)
    return libro, pid, c.post(f"/api/prestamos/{pid}/devolver")


def test_devolucion_a_tiempo_sin_adeudo(bibliotecario, monkeypatch):
    viernes = date(2026, 10, 30)
    libro, pid, r = _devolver_con_hoy(monkeypatch, bibliotecario, viernes, viernes)  # el dia de vencimiento no multa
    d = r.get_json()
    assert r.status_code == 200 and d["dias_retraso"] == 0 and d["adeudo"] is None and d["espera_notificada"] is None
    assert d["prestamo"]["estado"] == "devuelto" and d["prestamo"]["fecha_devolucion"]
    assert sql("SELECT count(*) AS n FROM adeudo WHERE id_prestamo=%s", (pid,))[0]["n"] == 0
    assert sql("SELECT estado FROM ejemplar WHERE id_libro=%s", (libro["id_libro"],))[0]["estado"] == "disponible"
    assert _bitacora("prestamo_devolver", f"{d['prestamo']['folio']}%")


def test_devolucion_un_dia_habil_tarde_y_fin_de_semana(bibliotecario, monkeypatch):
    viernes, lunes, martes = date(2026, 10, 30), date(2026, 11, 2), date(2026, 11, 3)
    _, pid, r = _devolver_con_hoy(monkeypatch, bibliotecario, lunes, viernes)  # vence viernes, lunes = 1 dia
    d = r.get_json()
    assert d["dias_retraso"] == 1 and d["adeudo"]["monto"] == 10.0 and d["adeudo"]["dias_retraso"] == 1
    fila = sql("SELECT tipo, monto, estado, dias_retraso FROM adeudo WHERE id_prestamo=%s", (pid,))[0]
    assert (fila["tipo"], float(fila["monto"]), fila["estado"], fila["dias_retraso"]) == ("retraso", 10.0, "pendiente", 1)
    _, pid2, r2 = _devolver_con_hoy(monkeypatch, bibliotecario, martes, viernes)
    assert r2.get_json()["dias_retraso"] == 2 and r2.get_json()["adeudo"]["monto"] == 20.0
    sabado, domingo = date(2026, 10, 31), date(2026, 11, 1)
    for hoy in (sabado, domingo):  # sabado y domingo no cuentan
        assert _devolver_con_hoy(monkeypatch, bibliotecario, hoy, viernes)[2].get_json()["adeudo"] is None


def test_devolver_dos_veces_y_inexistente(bibliotecario):
    _, pid = _loan_for(make_user())
    assert bibliotecario.post(f"/api/prestamos/{pid}/devolver").status_code == 200
    assert bibliotecario.post(f"/api/prestamos/{pid}/devolver").status_code == 409
    assert bibliotecario.post("/api/prestamos/999999/devolver").status_code == 404


def test_devolucion_notifica_al_primero_en_espera(bibliotecario):
    u, primero, segundo = make_user(), make_user(), make_user()
    libro, pid = _loan_for(u, ejemplares=1)
    sql("INSERT INTO lista_espera(id_usuario,id_libro,posicion) VALUES (%s,%s,2)", (segundo["id_usuario"], libro["id_libro"]))
    sql("INSERT INTO lista_espera(id_usuario,id_libro,posicion) VALUES (%s,%s,1)", (primero["id_usuario"], libro["id_libro"]))
    d = bibliotecario.post(f"/api/prestamos/{pid}/devolver").get_json()
    assert d["espera_notificada"]["id_usuario"] == primero["id_usuario"]
    filas = {r["id_usuario"]: r for r in sql("SELECT * FROM lista_espera WHERE id_libro=%s", (libro["id_libro"],))}
    n = filas[primero["id_usuario"]]
    assert n["estado"] == "notificado" and n["fecha_notificacion"] and n["fecha_limite_recoger"] > n["fecha_notificacion"]
    assert n["fecha_limite_recoger"].date() == calendario.sumar_habiles(date.today(), 2)
    assert filas[segundo["id_usuario"]]["estado"] == "en_espera"
    assert _bitacora("notif_email", f"{primero['correo']}|%")
    # el ejemplar queda reservado: solo el notificado puede llevarselo
    assert _codigos(_validar(bibliotecario, segundo, libro)) == {"LIBRO_RESERVADO_OTRO_USUARIO"}
    assert _prestar(bibliotecario, primero, libro).status_code == 201


# ------------------------------------------------------------------ listados
def test_listado_filtros_y_detalle(bibliotecario):
    u = make_user()
    _, pa = _loan_for(u)
    _, pv = _loan_for(u)
    _vence(pv, date.today() - timedelta(days=9))
    _, pd = _loan_for(u)
    _cerrar(pd)
    todos = bibliotecario.get(f"/api/prestamos?matricula={u['matricula']}").get_json()
    assert {p["id_prestamo"] for p in todos} == {pa, pv, pd}
    por_estado = {e: {p["id_prestamo"] for p in bibliotecario.get(f"/api/prestamos?estado={e}&q={u['matricula']}").get_json()}
                  for e in ("activo", "vencido", "devuelto")}
    assert por_estado == {"activo": {pa}, "vencido": {pv}, "devuelto": {pd}}
    v = next(p for p in todos if p["id_prestamo"] == pv)
    assert v["estado"] == "vencido" and v["dias_retraso"] > 0 and v["multa_estimada"] == v["dias_retraso"] * 10.0
    assert set(v) >= {"folio", "usuario", "libro", "id_ejemplar", "numero_copia", "max_renovaciones", "num_renovaciones"}
    assert v["usuario"]["rol"] == "alumno" and set(v["libro"]) == {"id_libro", "clave", "titulo"}
    assert len(bibliotecario.get(f"/api/prestamos?q={v['libro']['clave'].lower()}").get_json()) == 1
    d = bibliotecario.get(f"/api/prestamos/{pv}").get_json()
    assert d["renovaciones"] == [] and d["adeudos"] == []
    assert bibliotecario.get("/api/prestamos/999999").status_code == 404


def test_demo_sembrada_vencido_segun_d24(bibliotecario):
    r = bibliotecario.get("/api/prestamos?estado=vencido&matricula=A0512980")
    assert r.status_code == 200 and all(p["estado"] == "vencido" for p in r.get_json())


# ------------------------------------------------------------------ politicas
def test_politicas_get_y_put(admin, bibliotecario):
    pols = {p["rol"]: p for p in admin.get("/api/politicas").get_json()}
    alumno = pols["alumno"]
    assert alumno["dias_prestamo"] == 5 and alumno["max_libros"] == 2 and alumno["activa"] is True
    assert set(alumno) == {"id_politica", "rol", "dias_prestamo", "max_libros", "max_renovaciones", "multa_diaria", "activa"}
    ruta = f"/api/politicas/{alumno['id_politica']}"
    cuerpo = {k: alumno[k] for k in ("dias_prestamo", "max_libros", "max_renovaciones", "multa_diaria")}
    assert bibliotecario.put(ruta, json=cuerpo).status_code == 403
    try:
        r = admin.put(ruta, json={**cuerpo, "multa_diaria": 12.5, "max_renovaciones": 4})
        assert r.status_code == 200 and r.get_json()["multa_diaria"] == 12.5 and r.get_json()["max_renovaciones"] == 4
        assert _bitacora("politica_cambio", "%alumno%")
        # un prestamo ya creado conserva su id_politica
        for malo in ({"dias_prestamo": 0}, {"max_libros": -1}, {"max_renovaciones": "x"}, {"multa_diaria": -1},
                     {"dias_prestamo": 1.5}, {"multa_diaria": None}):
            assert admin.put(ruta, json={**cuerpo, **malo}).status_code == 400, malo
        assert admin.put(ruta, json={"dias_prestamo": 5}).status_code == 400
        assert admin.put("/api/politicas/999999", json=cuerpo).status_code == 404
    finally:
        assert admin.put(ruta, json=cuerpo).status_code == 200
