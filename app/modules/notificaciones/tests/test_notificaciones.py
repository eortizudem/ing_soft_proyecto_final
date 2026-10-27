from app.core import db, notificaciones
from app.testing import sql, uniq


def _enviar(app, canal, asunto, cuerpo, matricula):
    uid = sql("SELECT id_usuario FROM usuario WHERE matricula=%s", (matricula,))[0]["id_usuario"]
    with app.app_context():
        notificaciones.enviar_a_usuario(canal, asunto, cuerpo, uid)
        db.get_conn().commit()


def test_permisos(alumno, anon, bibliotecario):
    assert alumno.get("/api/notificaciones").status_code == 403
    assert anon.get("/api/notificaciones").status_code == 401
    assert anon.get("/api/notificaciones/mias").status_code == 401
    assert bibliotecario.get("/api/notificaciones").status_code == 200
    assert alumno.get("/api/notificaciones/mias").status_code == 200


def test_listado_filtros_y_mias(app, admin, alumno):
    tag = uniq()
    _enviar(app, "email", f"Aviso {tag}", "Cuerpo uno", "A0512345")
    _enviar(app, "tesoreria", f"Cobro {tag}", "Cuerpo dos", "A0512980")
    todas = admin.get("/api/notificaciones?q=" + tag).get_json()
    assert {n["canal"] for n in todas} == {"email", "tesoreria"}
    n = next(x for x in todas if x["canal"] == "email")
    assert n["asunto"] == f"Aviso {tag}" and n["cuerpo"] == "Cuerpo uno" and "@" in n["destino"]
    assert n["usuario"]["matricula"] == "A0512345" and n["fecha"] and n["id_bitacora"]
    solo = admin.get(f"/api/notificaciones?q={tag}&canal=tesoreria").get_json()
    assert [x["canal"] for x in solo] == ["tesoreria"]
    assert admin.get(f"/api/notificaciones?q={tag}&desde=2999-01-01").get_json() == []
    assert len(admin.get(f"/api/notificaciones?q={tag}&limite=1").get_json()) == 1
    assert admin.get("/api/notificaciones?canal=sms").status_code == 400
    assert admin.get("/api/notificaciones?desde=ayer").status_code == 400
    por_dest = admin.get("/api/notificaciones?q=A0512980").get_json()
    assert por_dest and all(x["usuario"]["matricula"] == "A0512980" or "A0512980" in x["destino"] for x in por_dest)
    mias = alumno.get("/api/notificaciones/mias?q=" + tag).get_json()
    assert [x["canal"] for x in mias] == ["email"]
    assert all(x["usuario"]["matricula"] == "A0512345" for x in alumno.get("/api/notificaciones/mias").get_json())


def test_solo_notificaciones(admin):
    sql("INSERT INTO bitacora(id_usuario, accion, detalle) SELECT id_usuario, 'login', 'zzqx-no-notif' FROM usuario LIMIT 1")
    assert admin.get("/api/notificaciones?q=zzqx-no-notif").get_json() == []


def test_visitante_sin_avisos(app):
    c = app.test_client()
    assert c.post("/api/visitante").status_code == 200
    assert c.get("/api/notificaciones/mias").get_json() == []
