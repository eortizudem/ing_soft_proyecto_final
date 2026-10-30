"""Capa SERVICE de errores (reglas de negocio): sanea y limita los errores reportados por el navegador y los registra en `bitacora` via `app.core.errores`.

No tiene capa model propia: la persistencia la hace `core.errores.registrar`.
"""
from flask import session

from app.core import errores

# Campos admitidos del reporte y su largo maximo (se truncan, no se rechazan).
_CAMPOS = (("mensaje", 120), ("ruta", 40), ("origen", 30))


def _texto(valor, largo):
    """Normaliza un campo de texto: colapsa espacios y trunca.

    Args:
        valor (Any): valor recibido (puede ser `None`).
        largo (int): longitud maxima.

    Returns:
        str: texto de una linea de hasta `largo` caracteres.
    """
    return " ".join(str(valor or "").split())[:largo]


def reportar(datos, cliente):
    """Registra un error del sistema del navegador. Si se excede el limite responde `registrado: False` sin error
    (el navegador no debe reaccionar con mas peticiones).

    No lanza `ApiError`: un mensaje vacio o un cliente sobre el limite (5/min por IP, 60/min global) simplemente
    no se registra. El detalle guardado es `"<ruta>: <mensaje> (<origen>)"` con origen `cliente`.

    Args:
        datos (dict): payload `{mensaje (max 120), ruta (max 40), origen (max 30)}`.
        cliente (str): identificador del cliente para el limite de frecuencia (IP).

    Returns:
        dict: `{"registrado": bool}`.
    """
    mensaje, ruta, origen = (_texto(datos.get(c), n) for c, n in _CAMPOS)
    if not mensaje or not errores.dentro_del_limite(cliente):
        return {"registrado": False}
    resumen = f"{ruta or '-'}: {mensaje}" + (f" ({origen})" if origen else "")
    return {"registrado": errores.registrar("cliente", resumen, session.get("uid"))}
