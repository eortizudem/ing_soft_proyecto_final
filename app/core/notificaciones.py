"""Avisos enviados, simulados (D-11): cada aviso es una fila de `bitacora` con accion 'notif_<canal>'.

`enviar` es el adaptador unico: cambiar a un proveedor real solo toca este archivo.
detalle = "<destino>|<asunto>: <cuerpo>" truncado a 200 caracteres.
"""
from . import bitacora, db
from .errors import ApiError

CANALES = ("email", "whatsapp", "servicios_escolares", "tesoreria")
PREFIJO = "notif_"


def validar_canales(canales, por_defecto=("email",)):
    """Lista de canales validos (sin repetidos, en orden); vacia/None -> `por_defecto`. 400 si alguno no existe."""
    canales = list(dict.fromkeys(canales or por_defecto))
    malos = [c for c in canales if c not in CANALES]
    if malos:
        raise ApiError(f"Canal de notificación no válido: {', '.join(map(str, malos))}.")
    return canales


def enviar(canal, asunto, cuerpo, id_usuario, destino=None):
    """Registra la notificacion. id_usuario = destinatario si existe; si no, quien origina el aviso (NOT NULL)."""
    if canal not in CANALES:
        raise ApiError(f"Canal de notificación no válido: {canal}.")
    bitacora.log(id_usuario, PREFIJO + canal, f"{destino or ''}|{asunto}: {cuerpo}")


def enviar_a_usuario(canal, asunto, cuerpo, id_usuario):
    """Como `enviar`, con destino = correo (email), telefono no existe -> matricula (resto de canales)."""
    u = db.fetchone("SELECT matricula, correo FROM usuario WHERE id_usuario=%s", (id_usuario,))
    destino = (u["correo"] if canal == "email" else u["matricula"]) if u else None
    enviar(canal, asunto, cuerpo, id_usuario, destino)


def parsear(accion, detalle):
    """(accion, detalle) de bitacora -> {canal, destino, asunto, cuerpo}. Inverso de `enviar`."""
    destino, _, resto = (detalle or "").partition("|")
    asunto, _, cuerpo = resto.partition(": ")
    return {"canal": accion[len(PREFIJO):], "destino": destino, "asunto": asunto, "cuerpo": cuerpo}
