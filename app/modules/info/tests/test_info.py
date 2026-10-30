"""Pruebas del modulo info: healthcheck, FAQ publica y respuestas JSON para rutas `/api` inexistentes."""
def test_health(anon):
    """`/api/health` responde ok con la base de datos disponible."""
    assert anon.get("/api/health").get_json() == {"ok": True, "db": True}


def test_faq_public(anon):
    """La FAQ es publica y trae al menos 5 preguntas con `pregunta`, `respuesta` y `categoria`."""
    j = anon.get("/api/faq").get_json()
    assert len(j) >= 5 and set(j[0]) == {"pregunta", "respuesta", "categoria"}


def test_unknown_api_is_json(anon):
    """Una ruta `/api` inexistente responde 404 en JSON."""
    r = anon.get("/api/nada")
    assert r.status_code == 404 and "error" in r.get_json()
