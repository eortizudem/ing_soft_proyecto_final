from flask import session

from app.core import errores

_CAMPOS = (("mensaje", 120), ("ruta", 40), ("origen", 30))


def _texto(valor, largo):
    return " ".join(str(valor or "").split())[:largo]


def reportar(datos, cliente):
    """Registra un error del sistema del navegador. Si se excede el limite responde `registrado: False` sin error
    (el navegador no debe reaccionar con mas peticiones)."""
    mensaje, ruta, origen = (_texto(datos.get(c), n) for c, n in _CAMPOS)
    if not mensaje or not errores.dentro_del_limite(cliente):
        return {"registrado": False}
    resumen = f"{ruta or '-'}: {mensaje}" + (f" ({origen})" if origen else "")
    return {"registrado": errores.registrar("cliente", resumen, session.get("uid"))}
