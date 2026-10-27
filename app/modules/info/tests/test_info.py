def test_health(anon):
    assert anon.get("/api/health").get_json() == {"ok": True, "db": True}


def test_faq_public(anon):
    j = anon.get("/api/faq").get_json()
    assert len(j) >= 5 and set(j[0]) == {"pregunta", "respuesta", "categoria"}


def test_unknown_api_is_json(anon):
    r = anon.get("/api/nada")
    assert r.status_code == 404 and "error" in r.get_json()
