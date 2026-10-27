from . import bp, service


@bp.get("/api/faq")
def faq():
    return service.faq()


@bp.get("/api/health")
def health():
    return service.health()
