import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from app.core import auth as core_auth
from app.core.bitacora import log
from app.core import notificaciones
from app.core.errors import ApiError
from app.core.validators import Str, validate

from . import model


PWD_CORTA = "La contraseña necesita al menos 6 caracteres."
LOGIN = {"matricula": Str(upper=True, required=False, default=""),
         "password": Str(strip=False, required=False, default="")}
RECUPERAR = {"correo": Str(required=False, default="")}
CONFIRMAR = {"password": Str("contraseña", min=6, strip=False, required_msg=PWD_CORTA, min_msg=PWD_CORTA),
             "token": Str("token")}


def _public(row):
    return {
        "id_usuario": row["id_usuario"],
        "matricula": row["matricula"],
        "nombre_completo": row["nombre_completo"],
        "correo": row["correo"],
        "rol": row["rol"],
        "rol_descripcion": row["rol_descripcion"],
        "permisos": model.permisos_habilitados(row["rol"]),
    }


def _visitante():
    rol = model.get_rol("visitante") or {"nombre": "visitante", "descripcion": "Visitante"}
    return _public({
        "id_usuario": None, "matricula": "VISITANTE", "nombre_completo": "Visitante", "correo": None,
        "rol": rol["nombre"], "rol_descripcion": rol["descripcion"],
    })


def user_from_session(session):
    if session.get("visitante"):
        return _visitante()
    uid = session.get("uid")
    if uid:
        row = model.find_by_id(uid)
        if row and row["estado"] == "activo":
            return _public(row)
    return None


def login(data):
    matricula, password = validate(data, LOGIN).values()
    row = model.find_by_matricula(matricula) if matricula else None
    if not row or not check_password_hash(row["contrasena_hash"], password):
        raise ApiError("Clave o contraseña incorrecta", 401)
    if row["estado"] != "activo":
        raise ApiError("La cuenta está inactiva", 403)
    core_auth.start_session(row["id_usuario"])
    log(row["id_usuario"], "login", f"Inicio de sesión de {row['matricula']}")
    return _public(row)


def visitante():
    core_auth.start_visitor_session()
    return _visitante()


def logout(user):
    if user:
        log(user["id_usuario"], "logout", f"Cierre de sesión de {user['matricula']}")
    core_auth.end_session()


def recuperar(data):
    correo = validate(data, RECUPERAR)["correo"]
    row = model.find_by_correo(correo) if correo else None
    if not row or row["estado"] != "activo":
        return None
    token = secrets.token_hex(24)
    model.create_token(row["id_usuario"], token, 30)
    log(row["id_usuario"], "recuperar_solicitud", "Solicitud de recuperación de contraseña")
    # Correo simulado (D-11): con DEMO_MOSTRAR_TOKEN=false este aviso es la unica via para obtener el codigo.
    notificaciones.enviar("email", "Recuperación de contraseña",
                          f"Tu código de recuperación es {token} (vence en 30 minutos).", row["id_usuario"], row["correo"])
    return token


def confirmar(data):
    c = validate(data, CONFIRMAR)
    password = c["password"]
    t = model.find_valid_token(c["token"])
    if not t:
        raise ApiError("El enlace de recuperación no es válido o ya expiró.")
    model.set_password(t["id_usuario"], generate_password_hash(password))
    model.mark_token_used(t["id_token"])
    log(t["id_usuario"], "password_reset", "Contraseña restablecida por recuperación")
