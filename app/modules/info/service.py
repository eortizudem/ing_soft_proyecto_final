from . import model


def faq():
    return model.faq()


def health():
    try:
        return {"ok": True, "db": model.ping()}, 200
    except Exception:
        return {"ok": False, "db": False}, 503
