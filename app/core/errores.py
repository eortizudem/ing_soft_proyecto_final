"""Bitacora de errores (PS-S3-06): errores 500 del servidor y errores de JavaScript del navegador.

Se escribe en `bitacora` con accion 'error_sistema' y detalle "<origen>|<resumen>". Usa su propia conexion con
autocommit: la peticion que fallo hace rollback y no debe llevarse el registro. Nunca lanza excepciones
(registrar un error del sistema no puede causar otro). `id_usuario` es NULL cuando no hay sesion (esquema S-6).
"""
import threading
import time

from . import db

ACCION = "error_sistema"
ORIGENES = ("servidor", "cliente")
# Limite contra inundacion (el endpoint del navegador es publico): por origen de red y global.
POR_CLIENTE = (5, 60)    # 5 errores por minuto por IP
GLOBAL = (60, 60)        # 60 errores por minuto en total
_recientes = {}
_cerrojo = threading.Lock()


def _permitido(clave, limite, ahora):
    maximo, ventana = limite
    marcas = [t for t in _recientes.get(clave, ()) if ahora - t < ventana]
    if len(marcas) >= maximo:
        _recientes[clave] = marcas
        return False
    marcas.append(ahora)
    _recientes[clave] = marcas
    return True


def dentro_del_limite(cliente, ahora=None):
    """True si `cliente` (p. ej. IP) puede registrar otro error ahora; cuenta la solicitud si es True."""
    ahora = time.monotonic() if ahora is None else ahora
    with _cerrojo:
        if len(_recientes) > 5000:  # evita crecer sin limite con muchas IP
            _recientes.clear()
        return _permitido(("ip", cliente), POR_CLIENTE, ahora) and _permitido("global", GLOBAL, ahora)


def reiniciar_limites():
    with _cerrojo:
        _recientes.clear()


def registrar(origen, resumen, id_usuario=None):
    """Guarda el error; devuelve True si quedo registrado."""
    detalle = f"{origen}|{' '.join(str(resumen).split())}"[:200]
    try:
        with db.connect() as conn:
            conn.execute("INSERT INTO bitacora(id_usuario, accion, detalle) VALUES (%s,%s,%s)",
                         (id_usuario, ACCION, detalle))
        return True
    except Exception:  # noqa: BLE001 - un fallo al registrar nunca debe ocultar el error original
        return False


def parsear(detalle):
    """detalle de bitacora -> (origen, resumen). Inverso de `registrar`."""
    origen, _, resumen = (detalle or "").partition("|")
    return origen, resumen
