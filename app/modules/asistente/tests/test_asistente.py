import time

import pytest

from app.testing import make_book, make_loan, make_user, sql, uniq


def say(client, texto, cid=None, **extra):
    r = client.post("/api/asistente/mensajes", json={"texto": texto, "id_conversacion": cid, **extra})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def intencion(client, texto):
    return say(client, texto)["respuesta"]["intencion"]


@pytest.fixture
def usuario(login_as):
    u = make_user()
    return u, login_as(u["matricula"], u["password"])


@pytest.fixture
def visitante(anon):
    assert anon.post("/api/visitante").status_code == 200
    return anon


def test_permisos(anon, alumno):
    assert anon.post("/api/asistente/mensajes", json={"texto": "hola"}).status_code == 401
    assert alumno.get("/api/asistente/consultas").status_code == 403
    assert alumno.post("/api/asistente/consultas/1/resolver", json={"respuesta": "x"}).status_code == 403


def test_validacion(alumno):
    assert alumno.post("/api/asistente/mensajes", json={"texto": ""}).status_code == 400
    assert alumno.post("/api/asistente/mensajes", json={"texto": "x" * 501}).status_code == 400
    assert alumno.post("/api/asistente/mensajes", json={"texto": "hola", "canal": "fax"}).status_code == 400
    assert alumno.post("/api/asistente/mensajes", json={"texto": "hola", "id_conversacion": 999999}).status_code == 404


def test_saludo_ayuda_despedida(alumno):
    assert intencion(alumno, "Hola, buenos días") == "saludo"
    assert intencion(alumno, "¿Qué puedes hacer?") == "ayuda"
    assert intencion(alumno, "Gracias, adiós") == "despedida"


def test_horarios(alumno):
    r = say(alumno, "¿A qué hora abre la biblioteca?")["respuesta"]
    assert r["intencion"] == "horarios" and "8:00" in r["texto"]


def test_reglas_reflejan_politica(alumno):
    r = say(alumno, "¿Cuántos libros puedo llevar en préstamo?")["respuesta"]
    assert r["intencion"] == "prestamo" and "2 libros" in r["texto"] and "5 días hábiles" in r["texto"]
    try:
        sql("UPDATE politica_prestamo SET max_libros=4, multa_diaria=12.50 WHERE activa AND "
            "id_rol=(SELECT id_rol FROM rol WHERE nombre='alumno')")
        r = say(alumno, "cuanto es la multa por retraso")["respuesta"]
        assert r["intencion"] == "multas" and "$12.50" in r["texto"]
        assert "4 libros" in say(alumno, "reglas de prestamo")["respuesta"]["texto"]
    finally:
        sql("UPDATE politica_prestamo SET max_libros=2, multa_diaria=10.00 WHERE activa AND "
            "id_rol=(SELECT id_rol FROM rol WHERE nombre='alumno')")


def test_renovacion_y_perdida(alumno):
    r = say(alumno, "¿Cómo renuevo mi libro?")["respuesta"]
    assert r["intencion"] == "renovacion" and "2" in r["texto"] and "periodo completo" in r["texto"]
    assert "reposición" in say(alumno, "Si pierdo un libro, ¿cuánto pago?")["respuesta"]["texto"]


def test_visitante_reglas_generales(visitante):
    r = say(visitante, "politicas de prestamo")["respuesta"]
    assert "Alumno" in r["texto"] and "Docente" in r["texto"]


def test_busqueda_con_resultados_sin_acentos_y_mayusculas(alumno):
    tag = uniq().lower()
    libro = make_book(titulo=f"Termodinámica {tag}", ejemplares=2)
    for texto in (f"Busco libros de TERMODINAMICA {tag}", f"tienen termodinámica {tag}?", f"donde esta {libro['clave']}"):
        r = say(alumno, texto)["respuesta"]
        assert r["libros"] and r["libros"][0]["id_libro"] == libro["id_libro"], texto
    b = say(alumno, f"busco termodinamica {tag}")["respuesta"]["libros"][0]
    assert b["disponibles"] == 2 and b["clave"] == libro["clave"] and "Planta" in b["ubicacion"]
    assert len(say(alumno, "libros de redes")["respuesta"].get("libros", [])) <= 5


def test_busqueda_sin_resultados(alumno):
    r = say(alumno, "busco el libro zzqxwv inexistente")["respuesta"]
    assert r["intencion"] == "buscar_libro" and not r.get("libros") and "No encontré" in r["texto"]


def test_busco_un_libro_sin_termino_pide_el_titulo(alumno):
    r = say(alumno, "Busco un libro")["respuesta"]
    assert r["intencion"] == "buscar_libro" and "título, autor o tema" in r["texto"]


def test_estatus_propio(usuario):
    u, c = usuario
    assert "No tienes préstamos" in say(c, "¿cuáles son mis préstamos?")["respuesta"]["texto"]
    libro = make_book(titulo=f"Libro prestado {uniq()}", ejemplares=1)
    pid = make_loan(u["id_usuario"], libro["id_libro"])
    r = say(c, "mis préstamos")["respuesta"]
    assert r["intencion"] == "estatus_prestamos" and libro["titulo"] in r["texto"] and "vence" in r["texto"]
    sql("UPDATE prestamo SET fecha_vencimiento = CURRENT_DATE - 10 WHERE id_prestamo=%s", (pid,))
    assert "VENCIDO" in say(c, "cuando vence mi prestamo")["respuesta"]["texto"]
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',2,20)", (pid,))
    r = say(c, "¿cuánto debo?")["respuesta"]
    assert r["intencion"] == "estatus_multas" and "$20.00" in r["texto"]


def test_visitante_sin_estatus(visitante):
    r = say(visitante, "mis prestamos")["respuesta"]
    assert r["intencion"] == "estatus_prestamos" and "iniciar sesión" in r["texto"]
    assert "iniciar sesión" in say(visitante, "tengo multas?")["respuesta"]["texto"]


def test_mensajes_persisten_con_intencion(alumno):
    out = say(alumno, "cual es el horario")
    cid = out["id_conversacion"]
    filas = sql("SELECT m.emisor, i.nombre FROM mensaje m JOIN intencion i USING (id_intencion) "
                "WHERE id_conversacion=%s ORDER BY id_mensaje", (cid,))
    assert [(f["emisor"], f["nombre"]) for f in filas] == [("usuario", "horarios"), ("asistente", "horarios")]
    say(alumno, "gracias", cid)
    got = alumno.get(f"/api/asistente/conversaciones/{cid}").get_json()
    assert [m["emisor"] for m in got["mensajes"]] == ["usuario", "asistente"] * 2 and got["resuelta"] is False


def test_paso_explicito_y_resolucion(usuario, bibliotecario):
    u, c = usuario
    out = say(c, "Quiero hablar con un bibliotecario")
    cid, r = out["id_conversacion"], out["respuesta"]
    assert r["con_bibliotecario"] and r["intencion"] == "pasar_a_bibliotecario"
    pend = bibliotecario.get("/api/asistente/consultas?estado=pendiente").get_json()
    fila = next(x for x in pend if x["id_conversacion"] == cid)
    assert fila["usuario"]["matricula"] == u["matricula"] and fila["resuelta"] is False and fila["ultimo_mensaje"]
    # el bibliotecario puede leer la conversacion; otro alumno no
    assert bibliotecario.get(f"/api/asistente/conversaciones/{cid}").status_code == 200
    assert bibliotecario.post(f"/api/asistente/consultas/{cid}/resolver", json={"respuesta": ""}).status_code == 400
    r = bibliotecario.post(f"/api/asistente/consultas/{cid}/resolver", json={"respuesta": "Ya te contacto."})
    assert r.status_code == 200 and r.get_json()["resuelta"] is True
    assert r.get_json()["mensajes"][-1]["texto"] == "[Bibliotecario] Ya te contacto."
    assert bibliotecario.post(f"/api/asistente/consultas/{cid}/resolver", json={"respuesta": "otra"}).status_code == 409
    assert sql("SELECT 1 FROM bitacora WHERE accion='asistente_resolver' AND detalle LIKE %s", (f"%{cid}%",))
    ids = [x["id_conversacion"] for x in bibliotecario.get("/api/asistente/consultas?estado=resuelta").get_json()]
    assert cid in ids
    assert cid not in [x["id_conversacion"] for x in bibliotecario.get("/api/asistente/consultas?estado=pendiente").get_json()]
    assert c.get(f"/api/asistente/conversaciones/{cid}").get_json()["mensajes"][-1]["texto"].startswith("[Bibliotecario]")


def test_resolver_inexistente_o_no_pasada(bibliotecario, alumno):
    cid = say(alumno, "hola")["id_conversacion"]
    assert bibliotecario.post(f"/api/asistente/consultas/{cid}/resolver", json={"respuesta": "x"}).status_code == 404
    assert bibliotecario.get(f"/api/asistente/conversaciones/{cid}").status_code == 404


def test_no_entendido_dos_veces_pasa_a_bibliotecario(alumno):
    a = say(alumno, "qwerty asdf zxcv")
    assert a["respuesta"]["intencion"] == "no_entendido" and not a["respuesta"]["con_bibliotecario"]
    b = say(alumno, "zzz yyy xxx", a["id_conversacion"])
    assert b["respuesta"]["con_bibliotecario"] and b["respuesta"]["intencion"] == "pasar_a_bibliotecario"


def test_calificacion(alumno, alumno2):
    cid = say(alumno, "hola")["id_conversacion"]
    assert alumno.post(f"/api/asistente/conversaciones/{cid}/opinion", json={"calificacion": 6}).status_code == 400
    assert alumno.post(f"/api/asistente/conversaciones/{cid}/opinion", json={}).status_code == 400
    r = alumno.post(f"/api/asistente/conversaciones/{cid}/opinion", json={"calificacion": 4, "resuelta": True})
    assert r.status_code == 200 and r.get_json()["calificacion"] == 4 and r.get_json()["resuelta"] is True
    assert alumno2.post(f"/api/asistente/conversaciones/{cid}/opinion", json={"calificacion": 1}).status_code == 404


def test_calificar_consulta_no_la_cierra(alumno, bibliotecario):
    cid = say(alumno, "quiero hablar con un bibliotecario")["id_conversacion"]
    r = alumno.post(f"/api/asistente/conversaciones/{cid}/opinion", json={"calificacion": 2, "resuelta": True})
    assert r.get_json()["resuelta"] is False
    assert cid in [x["id_conversacion"] for x in bibliotecario.get("/api/asistente/consultas?estado=pendiente").get_json()]


def test_aislamiento(alumno, alumno2, visitante):
    cid = say(alumno, "hola")["id_conversacion"]
    assert alumno2.get(f"/api/asistente/conversaciones/{cid}").status_code == 404
    assert alumno2.post("/api/asistente/mensajes", json={"texto": "hola", "id_conversacion": cid}).status_code == 404
    assert visitante.get(f"/api/asistente/conversaciones/{cid}").status_code == 404
    vid = say(visitante, "hola")["id_conversacion"]
    assert sql("SELECT id_usuario FROM conversacion WHERE id_conversacion=%s", (vid,))[0]["id_usuario"] is None
    assert visitante.get(f"/api/asistente/conversaciones/{vid}").status_code == 200
    assert alumno.get(f"/api/asistente/conversaciones/{vid}").status_code == 404


def test_latencia(alumno):
    t = time.perf_counter()
    say(alumno, "busco libros de ingenieria de software")
    say(alumno, "reglas de préstamo")
    assert time.perf_counter() - t < 3
