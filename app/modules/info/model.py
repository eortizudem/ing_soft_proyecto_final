from app.core import repo


def faq():
    return repo.fetch_all("SELECT pregunta, respuesta, categoria FROM pregunta_frecuente WHERE activa "
                       "ORDER BY id_pregunta")


def ping():
    return repo.fetch_one("SELECT 1 AS ok")["ok"] == 1
