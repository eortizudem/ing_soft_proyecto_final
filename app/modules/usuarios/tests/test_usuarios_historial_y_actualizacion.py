"""Pruebas funcionales de `usuarios`: historial (RF-04), actualización desde Servicios Escolares simulado e importación CSV (D-23, RF-03)."""

import json

import pytest

from app.modules.usuarios import service
from app.testing import libro_payload, make_book, make_loan, make_user, sql, uniq, user_payload


def _origen(tmp_path, monkeypatch, registros):
    """Helper: redirige `ARCHIVO_SIMULADO` a un JSON temporal con los `registros` dados."""
    f = tmp_path / "origen.json"
    f.write_text(json.dumps({"registros": registros}), encoding="utf-8")
    monkeypatch.setattr(service, "ARCHIVO_SIMULADO", f)


def _reg(**over):
    """Helper: genera un registro de origen válido y único; `over` sobrescribe campos."""
    s = uniq()
    d = {"matricula": f"S{s}", "nombre_completo": f"Alumno Origen {s}", "correo": f"s{s.lower()}@ducky.edu.mx",
         "rol": "alumno", "estado": "activo"}
    d.update(over)
    return d


def test_historial_permiso_y_404(alumno, anon, admin):
    """El historial exige permiso (403/401) y responde 404 para usuario inexistente."""
    assert alumno.get("/api/usuarios/1/historial").status_code == 403
    assert anon.get("/api/usuarios/1/historial").status_code == 401
    assert admin.get("/api/usuarios/999999/historial").status_code == 404


def test_historial_vacio(admin):
    """Un usuario nuevo tiene historial vacío."""
    u = admin.post("/api/usuarios", json=user_payload()).get_json()
    h = admin.get(f"/api/usuarios/{u['id_usuario']}/historial").get_json()
    assert h["prestamos"] == [] and h["renovaciones"] == [] and h["adeudos"] == [] and h["espera"] == []


def test_historial_con_datos_y_adeudos_monto_y_conteo(admin):
    """El historial incluye préstamos, renovaciones, adeudos y espera; el listado suma el monto y cuenta adeudos."""
    u = admin.post("/api/usuarios", json=user_payload()).get_json()
    uid = u["id_usuario"]
    lib = make_book()
    pr = make_loan(uid, lib["id_libro"])
    sql("INSERT INTO renovacion(id_prestamo, nueva_fecha_vencimiento) VALUES (%s, CURRENT_DATE+14)", (pr,))
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',2,10.50)", (pr,))
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'danio',0,5)", (pr,))
    sql("INSERT INTO lista_espera(id_usuario,id_libro) VALUES (%s,%s)", (uid, lib["id_libro"]))
    h = admin.get(f"/api/usuarios/{uid}/historial").get_json()
    assert h["prestamos"][0]["libro"] == {"clave": lib["clave"], "titulo": lib["titulo"]}
    assert h["prestamos"][0]["id_prestamo"] == pr and h["prestamos"][0]["estado"] == "activo"
    assert h["renovaciones"][0]["id_prestamo"] == pr
    assert {a["tipo"] for a in h["adeudos"]} == {"retraso", "danio"}
    assert h["espera"][0]["estado"] == "en_espera" and h["espera"][0]["libro"]["clave"] == lib["clave"]
    got = admin.get(f"/api/usuarios/{uid}").get_json()
    assert got["adeudos_pendientes"] == 15.5 and got["adeudos_pendientes_n"] == 2


def test_historial_bitacora(admin):
    """El historial incluye los eventos de bitácora del usuario."""
    u = admin.post("/api/usuarios", json=user_payload()).get_json()
    adm = sql("SELECT id_usuario FROM usuario WHERE matricula='ADM001'")[0]["id_usuario"]
    h = admin.get(f"/api/usuarios/{adm}/historial").get_json()
    assert any(b["accion"] == "usuario_crear" and u["matricula"] in b["detalle"] for b in h["bitacora"])


def test_sync_permiso(alumno):
    """La actualización desde Servicios Escolares exige permiso `usuarios`."""
    assert alumno.get("/api/usuarios/actualizar").status_code == 403
    assert alumno.post("/api/usuarios/actualizar", json={}).status_code == 403
    assert alumno.post("/api/usuarios/importar", json={"csv": "x"}).status_code == 403


def test_sync_archivo_real_vista_previa(admin):
    """La vista previa con el archivo simulado real devuelve registros y resumen."""
    r = admin.get("/api/usuarios/actualizar")
    assert r.status_code == 200 and r.get_json()["origen"] == "servicios_escolares"
    assert r.get_json()["registros"]


def test_sync_idempotente_y_cambios(admin, tmp_path, monkeypatch):
    """Aplicar la actualización crea/actualiza y una segunda ejecución no cambia nada."""
    nuevo = _reg()
    viejo = make_user(fuente_validacion="manual")
    cambio = _reg(matricula=viejo["matricula"], correo=viejo["correo"], nombre_completo="Nombre Nuevo")
    _origen(tmp_path, monkeypatch, [nuevo, cambio])
    prev = admin.get("/api/usuarios/actualizar").get_json()
    assert prev["resumen"] == {"nuevos": 1, "cambios": 1, "bajas": 0}
    r = admin.post("/api/usuarios/actualizar", json={}).get_json()
    assert (r["creados"], r["actualizados"], r["bajas"]) == (1, 1, 0) and r["omitidos"] == []
    assert r["credenciales_iniciales"][0]["matricula"] == nuevo["matricula"]
    row = sql("SELECT nombre_completo, fuente_validacion FROM usuario WHERE matricula=%s", (viejo["matricula"],))[0]
    assert row == {"nombre_completo": "Nombre Nuevo", "fuente_validacion": "servicios_escolares"}
    assert sql("SELECT fuente_validacion FROM usuario WHERE matricula=%s", (nuevo["matricula"],))[0][
        "fuente_validacion"] == "servicios_escolares"
    again = admin.post("/api/usuarios/actualizar", json={}).get_json()
    assert (again["creados"], again["actualizados"], again["bajas"], again["omitidos"]) == (0, 0, 0, [])
    assert admin.get("/api/usuarios/actualizar").get_json()["resumen"] == {"nuevos": 0, "cambios": 0, "bajas": 0}


def test_sync_baja_y_guarda(admin, tmp_path, monkeypatch):
    """La baja en origen desactiva la cuenta salvo que las guardas (préstamos/multas) la impidan."""
    libre, ocupado = make_user(fuente_validacion="servicios_escolares"), make_user(fuente_validacion="servicios_escolares")
    make_loan(ocupado["id_usuario"], make_book()["id_libro"])
    regs = [_reg(matricula=u["matricula"], correo=u["correo"], nombre_completo=u["nombre_completo"], estado="inactivo")
            for u in (libre, ocupado)]
    _origen(tmp_path, monkeypatch, regs)
    r = admin.post("/api/usuarios/actualizar", json={}).get_json()
    assert r["bajas"] == 1 and len(r["omitidos"]) == 1 and r["omitidos"][0]["matricula"] == ocupado["matricula"]
    assert sql("SELECT estado, registro_vigente FROM usuario WHERE matricula=%s", (libre["matricula"],))[0] == {
        "estado": "inactivo", "registro_vigente": False}
    assert sql("SELECT estado FROM usuario WHERE matricula=%s", (ocupado["matricula"],))[0]["estado"] == "activo"


def test_sync_omite_invalidos_y_correo_duplicado(admin, tmp_path, monkeypatch):
    """Se omiten registros inválidos o con correo ya usado, sin abortar el lote."""
    otro = make_user()
    regs = [_reg(correo=otro["correo"]), _reg(rol="admin"), _reg(correo="malo")]
    _origen(tmp_path, monkeypatch, regs)
    r = admin.post("/api/usuarios/actualizar", json={}).get_json()
    assert r["creados"] == 0 and len(r["omitidos"]) == 3


def test_importar_csv(admin):
    """La importación CSV crea, actualiza y reporta errores por línea con credenciales iniciales."""
    a, b = _reg(), _reg()
    existente = make_user(fuente_validacion="manual")
    csv_txt = ("matricula,nombre_completo,correo,rol,estado\n"
               f"{a['matricula']},{a['nombre_completo']},{a['correo']},alumno,activo\n"
               f"{existente['matricula']},Renombrado,{existente['correo']},alumno,activo\n"
               f"{a['matricula']},Duplicado,otro{a['correo']},alumno,activo\n"
               "FALTA,solo,tres\n"
               f"{b['matricula']},{b['nombre_completo']},correo-malo,alumno,activo\n"
               f"{b['matricula']},{b['nombre_completo']},{b['correo']},docente,\n")
    r = admin.post("/api/usuarios/importar", json={"csv": csv_txt})
    assert r.status_code == 200
    j = r.get_json()
    assert (j["creados"], j["actualizados"]) == (2, 1)
    assert [e["linea"] for e in j["errores"]] == [4, 5, 6]
    assert {c["matricula"] for c in j["credenciales_iniciales"]} == {a["matricula"], b["matricula"]}
    assert all(len(c["password"]) >= 6 for c in j["credenciales_iniciales"])
    assert sql("SELECT nombre_completo FROM usuario WHERE matricula=%s", (existente["matricula"],))[0][
        "nombre_completo"] == "Renombrado"
    again = admin.post("/api/usuarios/importar", json={"csv": csv_txt}).get_json()
    assert (again["creados"], again["actualizados"]) == (0, 0)


def test_importar_vacio(admin):
    """Importar un CSV vacío responde 400."""
    assert admin.post("/api/usuarios/importar", json={"csv": "  "}).status_code == 400
    assert admin.post("/api/usuarios/importar", json={}).status_code == 400


def test_listados_grandes_aceptan_limite(admin):
    """D-15: usuarios, prestamos y adeudos admiten ?limite= (por defecto 500, maximo 2000)."""
    for ruta in ("usuarios", "prestamos", "adeudos"):
        todos = admin.get(f"/api/{ruta}").get_json()
        uno = admin.get(f"/api/{ruta}?limite=1").get_json()
        assert len(uno) == min(1, len(todos)) and len(todos) <= 500, ruta
        assert admin.get(f"/api/{ruta}?limite=abc").status_code == 200
