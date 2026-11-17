"""Pruebas del cliente de Ollama `app/core/ia.py` (D-13): limpieza de `<think>`, errores tipados, estado recordado y,
si hay un Ollama real con el modelo descargado, una llamada de integracion."""
import pytest

from app.core import ia


@pytest.fixture
def con_ia(app, monkeypatch):
    """Activa la IA dentro de un contexto de app y limpia el estado recordado de `disponible()`."""
    monkeypatch.setitem(app.config, "ASISTENTE_IA", True)
    ia.olvidar_estado()
    with app.app_context():
        yield
    ia.olvidar_estado()


def test_limpiar_quita_razonamiento():
    """Quita `<think>...</think>` (incluso multilinea o sin cierre) y recorta."""
    assert ia.limpiar("<think>\nrazono\n</think>\n  Hola. ") == "Hola."
    assert ia.limpiar("Hola <think>sin cierre") == "Hola"
    assert ia.limpiar(None) == ""


def test_chat_arma_la_peticion_y_limpia(con_ia, monkeypatch):
    """Envia sistema + turnos, sin streaming ni razonamiento, y devuelve el texto limpio."""
    vistas = []
    monkeypatch.setattr(ia, "_pedir", lambda ruta, cuerpo=None, timeout=None: vistas.append((ruta, cuerpo)) or
                        {"message": {"content": "<think>x</think>Listo"}})
    assert ia.chat("sistema", [{"role": "user", "content": "hola"}], {"num_predict": 8}) == "Listo"
    ruta, cuerpo = vistas[0]
    assert ruta == "/api/chat" and cuerpo["stream"] is False and cuerpo["think"] is False
    assert cuerpo["messages"][0] == {"role": "system", "content": "sistema"} and cuerpo["options"]["num_predict"] == 8
    assert cuerpo["options"]["num_ctx"] == ia.OPCIONES["num_ctx"] and cuerpo["keep_alive"] == ia.MANTENER


def test_chat_errores_tipados(app, con_ia, monkeypatch):
    """Respuesta vacia, error de red y IA desactivada lanzan `IAError`."""
    monkeypatch.setattr(ia, "_pedir", lambda *a, **k: {"message": {"content": "<think>solo</think>"}})
    with pytest.raises(ia.IAError):
        ia.chat("s", [])
    monkeypatch.undo()                                                       # vuelve a `_pedir` real
    monkeypatch.setitem(app.config, "ASISTENTE_IA", True)
    monkeypatch.setitem(app.config, "OLLAMA_URL", "http://127.0.0.1:9")      # puerto cerrado
    with pytest.raises(ia.IAError):
        ia._pedir("/api/tags", timeout=1)
    monkeypatch.setitem(app.config, "ASISTENTE_IA", False)
    with pytest.raises(ia.IAError):
        ia.chat("s", [])


def test_disponible_requiere_el_modelo_y_recuerda(app, con_ia, monkeypatch):
    """Esta disponible solo si Ollama lista el modelo configurado; el resultado se recuerda y se puede olvidar."""
    monkeypatch.setitem(app.config, "OLLAMA_MODEL", "m:1")
    llamadas = []
    monkeypatch.setattr(ia, "_pedir", lambda ruta, cuerpo=None, timeout=None: llamadas.append(ruta) or {"models": [{"name": "m:1"}]})
    assert ia.disponible() and ia.disponible() and len(llamadas) == 1
    monkeypatch.setattr(ia, "_pedir", lambda *a, **k: {"models": [{"name": "otro:1"}]})
    ia.olvidar_estado()
    assert not ia.disponible()
    monkeypatch.setitem(app.config, "ASISTENTE_IA", False)
    assert not ia.disponible()


def test_integracion_ollama_real(app, monkeypatch):
    """Con un Ollama real y el modelo descargado, responde texto (se omite si no esta disponible)."""
    monkeypatch.setitem(app.config, "ASISTENTE_IA", True)
    ia.olvidar_estado()
    with app.app_context():
        if not ia.disponible():
            pytest.skip("Ollama no disponible o sin el modelo descargado")
        assert ia.chat("Responde solo con la palabra: listo.", [{"role": "user", "content": "hola"}], {"num_predict": 8})
