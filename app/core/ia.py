"""Cliente genérico de un LLM local servido por Ollama (D-13). Solo biblioteca estándar (`urllib`), sin dependencias nuevas.

Regla del proyecto: toda llamada a un modelo de lenguaje pasa por este módulo, siempre con un plan B (el llamador
decide que responder si lanza `IAError`) y sin enviar nunca datos de otros usuarios. El módulo no conoce la
biblioteca: recibe un texto de sistema y una lista de mensajes y devuelve texto.

Configuración (`app/config.py`): `ASISTENTE_IA` (activa/desactiva), `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`.
"""
import json
import re
import threading
import time
import urllib.request

from flask import current_app, has_app_context

from ..config import Config

# Opciones de generación pensadas para un modelo muy pequeño en CPU: poco azar, contexto corto y respuesta acotada.
OPCIONES = {"temperature": 0.2, "num_ctx": 2048, "num_predict": 256}
MANTENER = "10m"          # `keep_alive`: tiempo que el modelo permanece cargado en memoria tras cada petición
VIGENCIA_ESTADO = 10.0    # segundos que se recuerda el resultado de `disponible()`

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_cache = {"hasta": 0.0, "ok": False}
_cerrojo = threading.Lock()


class IAError(Exception):
    """El modelo no está disponible, tardó demasiado o respondió algo inutilizable."""


def _get(nombre):
    """Valor de configuración: `current_app.config` si hay contexto de app; si no, `Config`."""
    return current_app.config.get(nombre, getattr(Config, nombre)) if has_app_context() else getattr(Config, nombre)


def habilitada():
    """Indica si la IA está activada por configuración (`ASISTENTE_IA`); no comprueba que Ollama responda.

    Returns:
        bool: `True` si está activada.
    """
    return bool(_get("ASISTENTE_IA"))


def modelo():
    """Nombre del modelo configurado (`OLLAMA_MODEL`).

    Returns:
        str: p. ej. `"qwen2.5:0.5b"`.
    """
    return str(_get("OLLAMA_MODEL"))


def _url(ruta):
    """URL completa de un endpoint de Ollama.

    Args:
        ruta (str): ruta que empieza con `/api/`.

    Returns:
        str: URL absoluta.
    """
    return str(_get("OLLAMA_URL")).rstrip("/") + ruta


def _pedir(ruta, cuerpo=None, timeout=None):
    """Hace una petición JSON a Ollama.

    Args:
        ruta (str): endpoint (`/api/tags`, `/api/chat`).
        cuerpo (dict | None): JSON a enviar; `None` hace un GET.
        timeout (float | None): segundos; por defecto `OLLAMA_TIMEOUT`.

    Returns:
        dict: respuesta decodificada.

    Raises:
        IAError: ante cualquier error de red, tiempo agotado, HTTP o JSON inválido.
    """
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(_url(ruta), data=datos, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout or float(_get("OLLAMA_TIMEOUT"))) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001 - red, HTTP, tiempo agotado y JSON: todo se reporta como IAError
        raise IAError(f"{type(e).__name__}: {e}") from e


def disponible():
    """Indica si la IA está activada, Ollama responde y el modelo ya fue descargado. El resultado se recuerda
    `VIGENCIA_ESTADO` segundos para no consultar a Ollama en cada mensaje.

    Returns:
        bool: `True` si se puede intentar una respuesta con el modelo.
    """
    if not habilitada():
        return False
    with _cerrojo:
        ahora = time.monotonic()
        if ahora < _cache["hasta"]:
            return _cache["ok"]
    try:
        nombres = {m.get("name", "") for m in _pedir("/api/tags", timeout=2).get("models", [])}
        ok = modelo() in nombres or f"{modelo()}:latest" in nombres
    except IAError:
        ok = False
    with _cerrojo:
        _cache.update(hasta=time.monotonic() + VIGENCIA_ESTADO, ok=ok)
    return ok


def olvidar_estado():
    """Descarta el estado recordado de `disponible()` (tras un fallo o en pruebas)."""
    with _cerrojo:
        _cache.update(hasta=0.0, ok=False)


def limpiar(texto):
    """Quita las etiquetas de razonamiento `<think>...</think>` (y una apertura sin cierre) y recorta espacios.

    Args:
        texto (str | None): salida cruda del modelo.

    Returns:
        str: texto listo para mostrar.
    """
    t = _THINK.sub("", str(texto or ""))
    return t.split("<think>", 1)[0].strip()


def chat(sistema, mensajes, opciones=None):
    """Pide una respuesta al modelo (`/api/chat`, sin streaming, sin razonamiento visible).

    Args:
        sistema (str): instrucciones y contexto (rol `system`).
        mensajes (list[dict]): turnos previos y el actual, cada uno `{"role": "user" | "assistant", "content": str}`.
        opciones (dict | None): sobrescribe `OPCIONES` (p. ej. `{"num_predict": 8}`).

    Returns:
        str: respuesta del modelo, sin etiquetas `<think>` y recortada.

    Raises:
        IAError: si la IA esta desactivada, falla la llamada o la respuesta queda vacía.
    """
    if not habilitada():
        raise IAError("IA desactivada.")
    r = _pedir("/api/chat", {
        "model": modelo(), "stream": False, "think": False, "keep_alive": MANTENER,
        "options": {**OPCIONES, **(opciones or {})},
        "messages": [{"role": "system", "content": sistema}, *mensajes],
    })
    texto = limpiar((r.get("message") or {}).get("content"))
    if not texto:
        raise IAError("Respuesta vacía del modelo.")
    return texto
