import csv
import io
import json
import secrets
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

from app.core import circulacion
from app.core.bitacora import audit, log
from app.core.errors import ApiError
from app.core.estado import toggle_estado
from app.core.repo import or_404
from app.core.validators import CODE_RE, Email, Enum, Str, validate

from . import model

ESTADOS = ("activo", "inactivo")
FUENTES = ("servicios_escolares", "recursos_humanos", "manual")
ULTIMO_ADMIN = "Debe permanecer al menos un administrador activo."
NO_ENCONTRADA = "No se encontró la cuenta."

_PWD = dict(min=6, strict=True, min_msg="La contraseña necesita al menos 6 caracteres.", strip=False)
SCHEMA = {
    "matricula": Str("matrícula / nómina", upper=True, pattern=CODE_RE,
                     pattern_msg="La matrícula debe tener de 3 a 10 letras, números o guiones."),
    "nombre_completo": Str("nombre completo", max=120),
    "correo": Email("correo institucional", msg="Introduce un correo institucional válido."),
    "rol": Enum(model.roles_asignables, "Selecciona un perfil válido.", label="perfil"),
    "estado": Enum(ESTADOS, "Selecciona un estado válido.", label="estado"),
    "fuente_validacion": Enum(FUENTES, "Selecciona una origen del registro válida.", label="origen del registro"),
}
SCHEMA_CREAR = {**SCHEMA, "password": Str("contraseña", **_PWD)}
SCHEMA_EDITAR = {**SCHEMA, "password": Str("contraseña", required=False, **_PWD)}


def listar(q, rol, estado, limite=None):
    return model.list_(q, rol, estado, limite)


def obtener(id_usuario):
    return or_404(model.get(id_usuario), NO_ENCONTRADA)


def _clean(d, schema):
    data = validate(d, schema)
    data["password"] = generate_password_hash(data["password"]) if data.get("password") else None
    return data


def _guard_baja(target, actor):
    if target["id_usuario"] == actor["id_usuario"]:
        raise ApiError("No puedes dar de baja tu propia cuenta.")
    ctx = circulacion.contexto_usuario(target["id_usuario"])  # D-24: abierto = sin fecha_devolucion
    if ctx["prestamos_abiertos"] > 0 or ctx["adeudos_pendientes"] > 0:
        raise ApiError("No se puede dar de baja: la cuenta tiene préstamos o multas pendientes.")
    if target["rol"] == "admin" and model.count_active_admins(target["id_usuario"]) < 1:
        raise ApiError(ULTIMO_ADMIN)


@audit("usuario_crear", lambda u: f"Alta de {u['matricula']} ({u['rol']})")
def crear(d, actor):
    data = _clean(d, SCHEMA_CREAR)
    if model.find_conflict(data["matricula"], data["correo"]):
        raise ApiError("La matrícula o el correo ya están registrados.")
    inactivo = data["estado"] == "inactivo"
    data["registro_vigente"] = not inactivo
    data["fecha_baja"] = date.today() if inactivo else None
    return model.get(model.insert(data))


@audit("usuario_editar", lambda u: f"Edición de {u['matricula']}")
def actualizar(id_usuario, d, actor):
    old = obtener(id_usuario)
    data = _clean(d, SCHEMA_EDITAR)
    if model.find_conflict(data["matricula"], data["correo"], id_usuario):
        raise ApiError("La matrícula o el correo ya están registrados.")
    if old["id_usuario"] == actor["id_usuario"] and (data["rol"] != "admin" or data["matricula"] != old["matricula"]):
        raise ApiError("No puedes cambiar tu propia matrícula ni quitarte la administración.")
    if old["estado"] == "activo" and data["estado"] == "inactivo":
        _guard_baja(old, actor)
    if (old["rol"] == "admin" and old["estado"] == "activo"
            and (data["rol"] != "admin" or data["estado"] != "activo")
            and model.count_active_admins(id_usuario) < 1):
        raise ApiError(ULTIMO_ADMIN)
    if data["estado"] == old["estado"]:
        data["registro_vigente"], data["fecha_baja"] = old["registro_vigente"], old["fecha_baja"]
    elif data["estado"] == "inactivo":
        data["registro_vigente"], data["fecha_baja"] = False, date.today()
    else:
        data["registro_vigente"], data["fecha_baja"] = True, None
    model.update(id_usuario, data)
    return model.get(id_usuario)


@audit(lambda u: "usuario_baja" if u["estado"] == "inactivo" else "usuario_reactivar",
       lambda u: f"{'Baja' if u['estado'] == 'inactivo' else 'Reactivación'} de {u['matricula']}")
def alternar(id_usuario, actor):
    toggle_estado(
        "usuario", "id_usuario", id_usuario, load=obtener,
        guard=lambda u, nuevo: _guard_baja(u, actor) if nuevo == "inactivo" else None,
        extra={"inactivo": {"fecha_baja": date.today(), "registro_vigente": False},
               "activo": {"fecha_baja": None, "registro_vigente": True}})
    return model.get(id_usuario)


# --- Historial (RF-04) ---
def historial(id_usuario):
    obtener(id_usuario)
    prestamos = [{**{k: p[k] for k in ("id_prestamo", "fecha_prestamo", "fecha_vencimiento", "fecha_devolucion",
                                       "estado", "num_renovaciones")},
                  "libro": {"clave": p["libro_clave"], "titulo": p["libro_titulo"]}}
                 for p in model.historial_prestamos(id_usuario)]
    espera = [{"id_espera": w["id_espera"], "libro": {"clave": w["libro_clave"], "titulo": w["libro_titulo"]},
               "estado": w["estado"], "posicion": w["posicion"]} for w in model.historial_espera(id_usuario)]
    return {"prestamos": prestamos, "renovaciones": model.historial_renovaciones(id_usuario),
            "adeudos": model.historial_adeudos(id_usuario), "espera": espera,
            "bitacora": model.historial_bitacora(id_usuario)}


# --- Actualización desde Servicios Escolares (simulada) e importación de lista de alumnos (D-23, RF-03) ---
ARCHIVO_SIMULADO = Path(__file__).parent / "simulado" / "servicios_escolares.json"
FUENTE_LISTA = "servicios_escolares"
CAMPOS = ("nombre_completo", "correo", "rol", "estado")
_SCHEMA_REGISTRO = {k: SCHEMA[k] for k in ("matricula", "nombre_completo", "correo", "rol", "estado")}


def _leer_origen():
    try:
        data = json.loads(ARCHIVO_SIMULADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ApiError("No se pudo leer el archivo simulado de Servicios Escolares.", 500)
    return data.get("registros", []) if isinstance(data, dict) else []


def _normalizar(reg):
    """Valida un registro del lista de alumnos (reutiliza SCHEMA). Estado vacío = activo."""
    reg = {k: (v.strip() if isinstance(v, str) else v) for k, v in (reg or {}).items()}
    reg["estado"] = reg.get("estado") or "activo"
    return validate(reg, _SCHEMA_REGISTRO)


def _diferencias(old, new):
    out = [c for c in CAMPOS if (old[c] or "").lower() != (new[c] or "").lower()]
    if old["fuente_validacion"] != FUENTE_LISTA:
        out.append("fuente_validacion")
    return out


def _clasificar(reg):
    """-> (accion, detalle) con accion nuevo | cambio | baja | sin_cambios | omitido (detalle = campos o motivo)."""
    try:
        new = _normalizar(reg)
    except ApiError as e:
        return {"accion": "omitido", "motivo": e.message, "registro": reg}
    item = {"registro": new, "matricula": new["matricula"]}
    old = model.get_by_matricula(new["matricula"])
    if new["rol"] not in ("alumno", "docente"):
        return {**item, "accion": "omitido", "motivo": "Servicios Escolares solo administra alumnos y docentes."}
    if old and old["rol"] not in ("alumno", "docente"):
        return {**item, "accion": "omitido", "motivo": "La cuenta existente no es de alumno o docente."}
    if not old:
        if model.find_conflict(new["matricula"], new["correo"]):
            return {**item, "accion": "omitido", "motivo": "El correo ya está registrado en otra cuenta."}
        if new["estado"] == "inactivo":
            return {**item, "accion": "omitido", "motivo": "Registro dado de baja en origen y sin cuenta local."}
        return {**item, "accion": "nuevo", "cambios": list(CAMPOS)}
    if model.find_conflict(new["matricula"], new["correo"], old["id_usuario"]):
        return {**item, "accion": "omitido", "motivo": "El correo ya está registrado en otra cuenta."}
    cambios = _diferencias(old, new)
    if not cambios:
        return {**item, "accion": "sin_cambios", "cambios": []}
    baja = old["estado"] == "activo" and new["estado"] == "inactivo"
    return {**item, "accion": "baja" if baja else "cambio", "cambios": cambios, "id_usuario": old["id_usuario"]}


def _plan(registros):
    vistos, plan = set(), []
    for reg in registros:
        item = _clasificar(reg)
        m = item.get("matricula")
        if m and m in vistos:
            item = {**item, "accion": "omitido", "motivo": "Matrícula repetida en el origen."}
        vistos.add(m)
        plan.append(item)
    return plan


def _vista(item):
    out = {**(item.get("registro") or {}), "accion": item["accion"]}
    for k in ("cambios", "motivo"):
        if k in item:
            out[k] = item[k]
    return out


def previsualizar_actualizacion():
    plan = _plan(_leer_origen())
    cuenta = lambda a: sum(1 for i in plan if i["accion"] == a)  # noqa: E731
    return {"origen": "servicios_escolares", "registros": [_vista(i) for i in plan],
            "resumen": {"nuevos": cuenta("nuevo"), "cambios": cuenta("cambio"), "bajas": cuenta("baja")}}


def _aplicar(item, actor, creds):
    """Escribe un registro planeado (crear o actualizar) reutilizando crear/actualizar y sus guardas."""
    reg = {**item["registro"], "fuente_validacion": FUENTE_LISTA}
    if item["accion"] == "nuevo":
        password = secrets.token_urlsafe(9)
        crear({**reg, "password": password}, actor)
        creds.append({"matricula": reg["matricula"], "password": password})
    else:
        actualizar(item["id_usuario"], reg, actor)


def _ejecutar(plan, actor, detalle):
    res = {"creados": 0, "actualizados": 0, "bajas": 0, "omitidos": [], "credenciales_iniciales": []}
    for item in plan:
        if item["accion"] == "omitido":
            res["omitidos"].append({"matricula": item.get("matricula") or (item.get("registro") or {}).get("matricula", ""),
                                    "motivo": item["motivo"]})
        elif item["accion"] == "sin_cambios":
            continue
        else:
            try:
                _aplicar(item, actor, res["credenciales_iniciales"])
            except ApiError as e:  # guarda de baja, cuenta propia, último admin...
                res["omitidos"].append({"matricula": item["matricula"], "motivo": e.message})
                continue
            res[{"nuevo": "creados", "cambio": "actualizados", "baja": "bajas"}[item["accion"]]] += 1
    log(actor["id_usuario"], detalle[0],
        f"{res['creados']} creados, {res['actualizados']} actualizados, {res['bajas']} bajas, {len(res['omitidos'])} omitidos")
    return res


def actualizar_lista(actor):
    return _ejecutar(_plan(_leer_origen()), actor, ("usuario_sync",))


def importar_csv(texto, actor):
    texto = (texto or "").strip() if isinstance(texto, str) else ""
    if not texto:
        raise ApiError("Pega o carga el contenido del CSV.")
    filas = list(csv.reader(io.StringIO(texto)))
    cols = ("matricula", "nombre_completo", "correo", "rol", "estado")
    inicio = 1 if filas and [c.strip().lower() for c in filas[0][:1]] == ["matricula"] else 0
    errores, plan, vistos = [], [], set()
    for n, fila in enumerate(filas[inicio:], start=inicio + 1):
        if not any(c.strip() for c in fila):
            continue
        if len(fila) < 4 or len(fila) > 5:
            errores.append({"linea": n, "motivo": "Se esperan 4 o 5 columnas: matrícula, nombre, correo, perfil y estado."})
            continue
        item = _clasificar(dict(zip(cols, fila)))
        m = item.get("matricula")
        if m and item["accion"] != "omitido" and m in vistos:
            item = {**item, "accion": "omitido", "motivo": "Matrícula repetida en el archivo."}
        if item["accion"] == "omitido":
            errores.append({"linea": n, "motivo": item["motivo"]})
            continue
        vistos.add(m)
        plan.append({**item, "linea": n})
    res = _ejecutar(plan, actor, ("usuario_importar",))
    for o in res.pop("omitidos"):
        linea = next((i["linea"] for i in plan if i["matricula"] == o["matricula"]), 0)
        errores.append({"linea": linea, "motivo": o["motivo"]})
    errores.sort(key=lambda e: e["linea"])
    return {"creados": res["creados"], "actualizados": res["actualizados"], "bajas": res["bajas"],
            "errores": errores, "credenciales_iniciales": res["credenciales_iniciales"]}
