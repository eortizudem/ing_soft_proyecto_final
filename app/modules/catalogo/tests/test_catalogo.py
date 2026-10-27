from app.testing import libro_payload, make_loan, sql, user_payload


def test_permissions(alumno, anon):
    assert alumno.post("/api/libros", json=libro_payload()).status_code == 403
    assert anon.get("/api/libros").status_code == 401


def test_seed_books(alumno):
    libros = alumno.get("/api/libros").get_json()
    claves = {b["clave"]: b for b in libros}
    assert {"LIB001", "LIB006"} <= set(claves)
    b = claves["LIB001"]
    assert b["ejemplares"] == 5 and b["prestados"] == 2 and b["disponibles"] == 3
    assert b["ubicacion"] == {"planta": "Planta baja", "pasillo": "A", "librero": "03", "nivel": 2}
    assert b["precio_referencia"] == 850 and b["tipo_uso"] == "prestamo_externo"
    assert claves["LIB003"]["tipo_uso"] == "consulta_interna"


def test_create_update_stock(admin):
    r = admin.post("/api/libros", json=libro_payload(ejemplares=3, librero=7))
    assert r.status_code == 201
    b = r.get_json()
    assert b["ejemplares"] == 3 and b["disponibles"] == 3 and b["ubicacion"]["librero"] == "07"
    p = libro_payload(clave=b["clave"], ejemplares=6)
    j = admin.put(f"/api/libros/{b['id_libro']}", json=p).get_json()
    assert j["ejemplares"] == 6 and j["disponibles"] == 6
    j = admin.put(f"/api/libros/{b['id_libro']}", json={**p, "ejemplares": 2}).get_json()
    assert j["ejemplares"] == 2 and j["disponibles"] == 2


def test_validation(admin):
    ok = admin.post("/api/libros", json=libro_payload()).get_json()
    assert admin.post("/api/libros", json=libro_payload(clave=ok["clave"])).status_code == 400
    for bad in ({"ejemplares": 0}, {"ejemplares": 10001}, {"ejemplares": "x"}, {"anio_publicacion": 999},
                {"anio_publicacion": 2101}, {"precio_referencia": -1}, {"tipo_uso": "otro"}, {"librero": 13},
                {"librero": 0}, {"clave": "ab"}, {"titulo": ""}):
        r = admin.post("/api/libros", json=libro_payload(**bad))
        assert r.status_code == 400 and r.get_json()["error"], bad


def test_stock_below_prestados_and_toggle_with_loans(admin):
    u = admin.post("/api/usuarios", json=user_payload()).get_json()
    p = libro_payload(ejemplares=3)
    b = admin.post("/api/libros", json=p).get_json()
    make_loan(u["id_usuario"], b["id_libro"])
    make_loan(u["id_usuario"], b["id_libro"])
    got = admin.get(f"/api/libros/{b['id_libro']}").get_json()
    assert got["prestados"] == 2 and got["disponibles"] == 1
    r = admin.put(f"/api/libros/{b['id_libro']}", json={**p, "ejemplares": 1})
    assert r.status_code == 400 and "prestadas" in r.get_json()["error"]
    j = admin.put(f"/api/libros/{b['id_libro']}", json={**p, "ejemplares": 2}).get_json()
    assert j["ejemplares"] == 2 and j["prestados"] == 2 and j["disponibles"] == 0
    r = admin.post(f"/api/libros/{b['id_libro']}/toggle")
    assert r.status_code == 400 and "préstamos activos" in r.get_json()["error"]
    assert admin.put(f"/api/libros/{b['id_libro']}", json={**p, "ejemplares": 2, "estado": "inactivo"}).status_code == 400


def test_toggle_and_visibility(admin, alumno):
    b = admin.post("/api/libros", json=libro_payload()).get_json()
    j = admin.post(f"/api/libros/{b['id_libro']}/toggle").get_json()
    assert j["estado"] == "inactivo" and j["disponibles"] == 0 and j["ejemplares"] == 3
    assert b["clave"] in [x["clave"] for x in admin.get("/api/libros?estado=inactivo").get_json()]
    assert b["clave"] not in [x["clave"] for x in alumno.get("/api/libros").get_json()]
    assert alumno.get(f"/api/libros/{b['id_libro']}").status_code == 404
    assert admin.post(f"/api/libros/{b['id_libro']}/toggle").get_json()["estado"] == "activo"


def test_accent_insensitive_search(alumno):
    def claves(q):
        return [b["clave"] for b in alumno.get("/api/libros", query_string={"q": q}).get_json()]
    assert "LIB001" in claves("ingenieria de software")
    assert "LIB001" in claves("INGENIERÍA")
    assert claves("calculo") == ["LIB004"]
    assert claves("CÁLCULO") == ["LIB004"]
    assert claves("paramo") == ["LIB003"]
    assert "LIB006" in claves("exupéry")
    assert claves("zzzz-no-existe") == []
    assert claves("100%") == []


def test_filters_and_temas(alumno):
    assert "Literatura" in alumno.get("/api/temas").get_json()
    lit = alumno.get("/api/libros?tema=Literatura").get_json()
    assert {b["clave"] for b in lit} >= {"LIB003", "LIB006"}
    assert all(b["disponibles"] > 0 for b in alumno.get("/api/libros?disponibles=1").get_json())


# ---- E2: ejemplares, baja/reactivar, etiqueta, pendientes, importación, reservado ----
import pytest

from app.core import circulacion
from app.testing import uniq


def _libro(admin, **over):
    return admin.post("/api/libros", json=libro_payload(**over)).get_json()


def _ejemplares(admin, b):
    return admin.get(f"/api/libros/{b['id_libro']}/ejemplares").get_json()


def test_ejemplares_listado_y_permisos(admin, alumno, bibliotecario):
    b = _libro(admin, ejemplares=2)
    ej = _ejemplares(admin, b)
    assert [e["numero_copia"] for e in ej] == [1, 2]
    assert all(e["estado"] == "disponible" and e["motivo_baja"] is None and e["prestamo_activo"] is None for e in ej)
    assert bibliotecario.get(f"/api/libros/{b['id_libro']}/ejemplares").status_code == 200
    assert alumno.get(f"/api/libros/{b['id_libro']}/ejemplares").status_code == 403
    assert alumno.post(f"/api/ejemplares/{ej[0]['id_ejemplar']}/baja", json={"motivo": "perdido"}).status_code == 403
    assert admin.get("/api/libros/999999/ejemplares").status_code == 404


@pytest.mark.parametrize("motivo", ["perdido", "robado", "danado", "obsoleto"])
def test_baja_y_reactivar_ejemplar(admin, motivo):
    b = _libro(admin, ejemplares=2)
    ej = _ejemplares(admin, b)[0]
    r = admin.post(f"/api/ejemplares/{ej['id_ejemplar']}/baja", json={"motivo": motivo, "observacion": "prueba"})
    assert r.status_code == 200 and r.get_json()["estado"] == "baja" and r.get_json()["motivo_baja"] == motivo
    got = admin.get(f"/api/libros/{b['id_libro']}").get_json()
    assert got["ejemplares"] == 1 and got["disponibles"] == 1
    assert sql("SELECT 1 FROM bitacora WHERE accion='ejemplar_baja' AND detalle LIKE %s", (f"%{b['clave']}-01 ({motivo})%",))
    assert admin.post(f"/api/ejemplares/{ej['id_ejemplar']}/baja", json={"motivo": motivo}).status_code == 409
    r = admin.post(f"/api/ejemplares/{ej['id_ejemplar']}/reactivar", json={})
    assert r.get_json()["estado"] == "disponible" and r.get_json()["motivo_baja"] is None
    assert admin.get(f"/api/libros/{b['id_libro']}").get_json()["disponibles"] == 2
    assert admin.post(f"/api/ejemplares/{ej['id_ejemplar']}/reactivar", json={}).status_code == 409


def test_baja_motivo_invalido_y_prestado(admin):
    b = _libro(admin, ejemplares=1)
    u = admin.post("/api/usuarios", json=user_payload()).get_json()
    make_loan(u["id_usuario"], b["id_libro"])
    ej = _ejemplares(admin, b)[0]
    assert ej["prestamo_activo"]["matricula"] == u["matricula"]
    r = admin.post(f"/api/ejemplares/{ej['id_ejemplar']}/baja", json={"motivo": "perdido"})
    assert r.status_code == 409 and "Multas y pagos" in r.get_json()["error"]
    assert admin.post(f"/api/ejemplares/{ej['id_ejemplar']}/baja", json={"motivo": "x"}).status_code == 400
    assert admin.post(f"/api/ejemplares/{ej['id_ejemplar']}/baja", json={}).status_code == 400
    assert admin.post("/api/ejemplares/999999/baja", json={"motivo": "perdido"}).status_code == 404


def test_reactivar_con_libro_inactivo_y_baja_masiva_conserva_motivo(admin):
    b = _libro(admin, ejemplares=3)
    ej = _ejemplares(admin, b)
    admin.post(f"/api/ejemplares/{ej[0]['id_ejemplar']}/baja", json={"motivo": "robado"})
    admin.post(f"/api/libros/{b['id_libro']}/toggle")
    assert admin.post(f"/api/ejemplares/{ej[0]['id_ejemplar']}/reactivar", json={}).status_code == 409
    admin.post(f"/api/libros/{b['id_libro']}/toggle")
    admin.put(f"/api/libros/{b['id_libro']}", json=libro_payload(clave=b["clave"], ejemplares=1))
    bajas = [e for e in _ejemplares(admin, b) if e["estado"] == "baja"]
    assert len(bajas) == 2 and all(e["motivo_baja"] for e in bajas)


def test_reservado_no_prestable(app, admin, alumno):
    b = _libro(admin, tipo_uso="reservado")
    assert b["tipo_uso"] == "reservado"
    uid = sql("SELECT id_usuario FROM usuario LIMIT 1")[0]["id_usuario"]
    with app.app_context():
        r = circulacion.autorizar_prestamo(uid, b["id_libro"])
    assert circulacion.LIBRO_NO_PRESTABLE in [m["codigo"] for m in r["motivos"]]
    assert b["clave"] in [x["clave"] for x in alumno.get("/api/libros?tipo_uso=reservado").get_json()]


def test_etiqueta(admin, alumno):
    b = _libro(admin, ejemplares=2)
    ej = _ejemplares(admin, b)
    admin.post(f"/api/ejemplares/{ej[0]['id_ejemplar']}/baja", json={"motivo": "danado"})
    j = admin.get(f"/api/libros/{b['id_libro']}/etiqueta").get_json()
    assert j["clave"] == b["clave"] and j["clasificacion"] == "000 PRU" and j["ubicacion"]["pasillo"] == "A"
    assert j["codigo_ejemplares"] == [{"numero_copia": 2, "etiqueta": f"{b['clave']}-02"}]
    assert alumno.get(f"/api/libros/{b['id_libro']}/etiqueta").status_code == 403
    assert admin.get("/api/libros/999999/etiqueta").status_code == 404


def _linea(recibida):
    uid = sql("SELECT id_usuario FROM usuario LIMIT 1")[0]["id_usuario"]
    folio = "P" + uniq(8)
    sid = sql("INSERT INTO solicitud_compra(folio,id_usuario,justificacion,estado) VALUES (%s,%s,'prueba','recibida') "
              "RETURNING id_solicitud", (folio, uid))[0]["id_solicitud"]
    det = sql("INSERT INTO detalle_solicitud(id_solicitud,descripcion,cantidad,cantidad_recibida,precio_unitario) "
              "VALUES (%s,'Libro nuevo de prueba',5,%s,12.50) RETURNING id_detalle", (sid, recibida))[0]["id_detalle"]
    return folio, det


def test_pendientes_y_enlace_id_detalle(admin, alumno):
    folio, det = _linea(2)
    _, sin_recibir = _linea(0)
    pend = admin.get("/api/libros/pendientes").get_json()
    assert alumno.get("/api/libros/pendientes").status_code == 403
    assert [p for p in pend if p["id_detalle"] == det] == [
        {"id_detalle": det, "descripcion": "Libro nuevo de prueba", "cantidad_recibida": 2, "precio_unitario": 12.5,
         "folio": folio}]
    assert sin_recibir not in [p["id_detalle"] for p in pend]
    b = admin.post("/api/libros", json=libro_payload(id_detalle=det)).get_json()
    assert sql("SELECT id_libro FROM detalle_solicitud WHERE id_detalle=%s", (det,))[0]["id_libro"] == b["id_libro"]
    assert det not in [p["id_detalle"] for p in admin.get("/api/libros/pendientes").get_json()]
    assert admin.post("/api/libros", json=libro_payload(id_detalle=det)).status_code == 409
    assert admin.post("/api/libros", json=libro_payload(id_detalle=999999)).status_code == 404


def test_filtros_por_campo_y_disponibilidad(alumno, admin):
    def claves(**qs):
        return [b["clave"] for b in alumno.get("/api/libros", query_string=qs).get_json()]
    assert claves(clave="lib001") == ["LIB001"]
    assert claves(autor="Exupery") == ["LIB006"]
    assert "LIB001" in claves(titulo="ingenieria")
    ed = alumno.get("/api/libros", query_string={"q": "LIB001"}).get_json()[0]["editorial"]
    assert "LIB001" in claves(editorial=ed.upper())
    b = _libro(admin, ejemplares=1)
    u = admin.post("/api/usuarios", json=user_payload()).get_json()
    make_loan(u["id_usuario"], b["id_libro"])
    assert b["clave"] in claves(disponibilidad="agotado") and b["clave"] not in claves(disponibilidad="disponible")
    assert "LIB001" in claves(disponibilidad="disponible")


def test_importar_csv(admin, alumno):
    s = uniq()
    csv_text = ("clave,titulo,autor,editorial,tema,anio_publicacion,clasificacion,sinopsis,precio_referencia,ejemplares\n"
                f"IM{s},Uno,Autor A,Ed,Tema,2020,000 A,Sinopsis,50,2\n"
                f"IM{s},Duplicado,Autor A,Ed,Tema,2020,000 A,Sinopsis,50,2\n"
                f"IN{s},Malo,Autor,Ed,Tema,1,000 A,Sinopsis,50,2\n")
    r = admin.post("/api/libros/importar", json={"csv": csv_text})
    j = r.get_json()
    assert r.status_code == 200 and j["creados"] == 1 and [e["linea"] for e in j["errores"]] == [3, 4]
    assert all(e["motivo"] for e in j["errores"])
    assert admin.post("/api/libros/importar", json={"csv": ""}).status_code == 400
    assert alumno.post("/api/libros/importar", json={"csv": csv_text}).status_code == 403
