from app.testing import make_book, make_loan, make_user, sql


def _agotado(ejemplares=1, **over):
    """Libro prestable cuyos ejemplares estan todos prestados (a un tercero)."""
    libro = make_book(ejemplares=ejemplares, **over)
    dueno = make_user()
    for _ in range(ejemplares):
        make_loan(dueno["id_usuario"], libro["id_libro"])
    return libro


def _alta(cli, usuario, libro):
    return cli.post("/api/espera", json={"matricula": usuario["matricula"], "id_libro": libro["id_libro"]})


def _codigos(r):
    return {m["codigo"] for m in r.get_json()["motivos"]}


def test_permisos(alumno, anon, bibliotecario):
    assert alumno.get("/api/espera").status_code == 403
    assert alumno.post("/api/espera", json={}).status_code == 403
    assert anon.get("/api/espera").status_code == 401
    assert anon.get("/api/espera/mias").status_code == 401
    assert bibliotecario.get("/api/espera").status_code == 200


def test_demo_maria_en_espera_lib005(bibliotecario):
    r = bibliotecario.get("/api/espera?q=LIB005").get_json()
    e = [x for x in r if x["usuario"]["matricula"] == "A0512345"][0]
    assert e["estado"] == "en_espera" and e["posicion"] == 1 and e["libro"]["disponibles"] == 0


def test_fifo_posiciones_y_renumeracion(bibliotecario):
    libro = _agotado()
    us = [make_user() for _ in range(3)]
    ids = []
    for i, u in enumerate(us, 1):
        r = _alta(bibliotecario, u, libro)
        assert r.status_code == 201
        e = r.get_json()
        assert e["posicion"] == i and e["estado"] == "en_espera" and e["libro"]["id_libro"] == libro["id_libro"]
        ids.append(e["id_espera"])
    r = bibliotecario.delete(f"/api/espera/{ids[0]}")
    assert r.status_code == 200 and r.get_json()["estado"] == "cancelado"
    lista = bibliotecario.get(f"/api/espera?id_libro={libro['id_libro']}&estado=en_espera").get_json()
    assert [(x["id_espera"], x["posicion"]) for x in lista] == [(ids[1], 1), (ids[2], 2)]
    assert bibliotecario.delete(f"/api/espera/{ids[0]}").status_code == 409
    # tras cancelar, el usuario puede volver a la fila (al final)
    assert _alta(bibliotecario, us[0], libro).get_json()["posicion"] == 3


def test_rechazos(bibliotecario):
    libro = _agotado()
    u = make_user()
    assert _alta(bibliotecario, u, libro).status_code == 201
    r = _alta(bibliotecario, u, libro)
    assert r.status_code == 422 and "YA_EN_ESPERA" in _codigos(r)
    # con ejemplares disponibles
    libre = make_book(ejemplares=2)
    r = _alta(bibliotecario, u, libre)
    assert r.status_code == 422 and "HAY_DISPONIBLES" in _codigos(r)
    # consulta interna / inactivo
    assert "LIBRO_NO_PRESTABLE" in _codigos(_alta(bibliotecario, u, make_book(tipo_uso="consulta_interna")))
    assert "LIBRO_NO_PRESTABLE" in _codigos(_alta(bibliotecario, u, make_book(estado="inactivo")))
    # usuario inactivo
    assert "USUARIO_INACTIVO" in _codigos(_alta(bibliotecario, make_user(estado="inactivo"), libro))
    # ya tiene el libro prestado
    dueno = sql("SELECT u.* FROM prestamo p JOIN ejemplar e ON e.id_ejemplar=p.id_ejemplar "
                "JOIN usuario u ON u.id_usuario=p.id_usuario WHERE e.id_libro=%s", (libro["id_libro"],))[0]
    assert "YA_TIENE_PRESTAMO" in _codigos(_alta(bibliotecario, dueno, libro))
    # validacion / inexistentes
    assert bibliotecario.post("/api/espera", json={"matricula": u["matricula"]}).status_code == 400
    assert bibliotecario.post("/api/espera", json={"matricula": "NOEXISTE", "id_libro": libro["id_libro"]}).status_code == 404
    assert bibliotecario.post("/api/espera", json={"matricula": u["matricula"], "id_libro": 99999999}).status_code == 404


def test_expiracion_pasa_al_siguiente(bibliotecario):
    libro = _agotado()
    u1, u2 = make_user(), make_user()
    e1 = _alta(bibliotecario, u1, libro).get_json()
    e2 = _alta(bibliotecario, u2, libro).get_json()
    # simula la devolucion de A: el ejemplar queda libre y el primero 'notificado' con plazo vencido
    sql("UPDATE ejemplar SET estado='disponible' WHERE id_libro=%s", (libro["id_libro"],))
    sql("UPDATE lista_espera SET estado='notificado', fecha_notificacion=now()-interval '5 days', "
        "fecha_limite_recoger=now()-interval '1 minute' WHERE id_espera=%s", (e1["id_espera"],))
    lista = {x["id_espera"]: x for x in bibliotecario.get(f"/api/espera?id_libro={libro['id_libro']}").get_json()}
    assert lista[e1["id_espera"]]["estado"] == "cancelado"
    n = lista[e2["id_espera"]]
    assert n["estado"] == "notificado" and n["posicion"] == 1 and n["fecha_limite_recoger"]
    hoy = sql("SELECT (now() + interval '1 day')::date AS d")[0]["d"]
    assert str(n["fecha_limite_recoger"])[:10] >= str(hoy)
    assert sql("SELECT count(*) AS n FROM bitacora WHERE accion='notif_email' AND detalle LIKE %s",
               (f"{u2['correo']}|%",))[0]["n"] == 1
    # idempotente: otra consulta no vuelve a notificar
    bibliotecario.get("/api/espera")
    assert sql("SELECT count(*) AS n FROM bitacora WHERE accion='notif_email' AND detalle LIKE %s",
               (f"{u2['correo']}|%",))[0]["n"] == 1


def test_plazo_en_dias_habiles(bibliotecario):
    from datetime import date

    from app.core import calendario
    libro = _agotado()
    u1, u2 = make_user(), make_user()
    _alta(bibliotecario, u1, libro)
    e2 = _alta(bibliotecario, u2, libro).get_json()
    sql("UPDATE ejemplar SET estado='disponible' WHERE id_libro=%s", (libro["id_libro"],))
    r = bibliotecario.get(f"/api/espera?id_libro={libro['id_libro']}").get_json()
    n = [x for x in r if x["posicion"] == 1][0]
    assert n["estado"] == "notificado"
    limite = n["fecha_limite_recoger"][:10]
    assert limite == calendario.sumar_habiles(date.today(), 2).isoformat()
    assert e2["id_espera"] != n["id_espera"]


def test_cancelar_notificado_avanza_la_fila(bibliotecario):
    libro = _agotado()
    u1, u2 = make_user(), make_user()
    e1 = _alta(bibliotecario, u1, libro).get_json()
    e2 = _alta(bibliotecario, u2, libro).get_json()
    sql("UPDATE ejemplar SET estado='disponible' WHERE id_libro=%s", (libro["id_libro"],))
    bibliotecario.get("/api/espera")  # promueve a e1
    assert bibliotecario.delete(f"/api/espera/{e1['id_espera']}").status_code == 200
    lista = {x["id_espera"]: x for x in bibliotecario.get(f"/api/espera?id_libro={libro['id_libro']}").get_json()}
    assert lista[e2["id_espera"]]["estado"] == "notificado" and lista[e2["id_espera"]]["posicion"] == 1


def test_usuario_une_cancela_y_ve_sus_solicitudes(alumno, alumno2, bibliotecario):
    libro = _agotado()
    r = alumno.post("/api/espera/unirse", json={"id_libro": libro["id_libro"]})
    assert r.status_code == 201 and r.get_json()["usuario"]["matricula"] == "A0512345"
    r2 = alumno.post("/api/espera/unirse", json={"id_libro": libro["id_libro"]})
    assert r2.status_code == 422 and "YA_EN_ESPERA" in _codigos(r2)
    mias = alumno.get("/api/espera/mias").get_json()
    assert [m["libro"]["id_libro"] for m in mias].count(libro["id_libro"]) == 1
    assert all(m["usuario"]["matricula"] == "A0512345" for m in mias)
    id_e = r.get_json()["id_espera"]
    assert alumno2.delete(f"/api/espera/{id_e}").status_code == 403
    assert alumno.delete(f"/api/espera/{id_e}").get_json()["estado"] == "cancelado"
    assert bibliotecario.get("/api/espera/libros").status_code == 200


def test_visitante_no_puede_unirse(anon):
    anon.post("/api/visitante")
    assert anon.post("/api/espera/unirse", json={"id_libro": 1}).status_code == 403


def test_bitacora(bibliotecario):
    libro = _agotado()
    u = make_user()
    e = _alta(bibliotecario, u, libro).get_json()
    bibliotecario.delete(f"/api/espera/{e['id_espera']}")
    acciones = {r["accion"] for r in sql("SELECT accion FROM bitacora WHERE detalle LIKE %s", (f"%{u['matricula']}%",))}
    assert {"espera_alta", "espera_cancelar"} <= acciones
