"""Fábrica de la aplicación Flask: configuración, BD, errores, módulos MVC y semilla inicial."""
import logging
import os

from flask import Flask, jsonify, send_from_directory

from .config import Config
from .core import db, excepciones
from .core.module import register_modules
from .core.serializers import JSONProvider


def create_app(config=None):
    """Construye y configura la aplicación Flask.

    Carga `Config`, registra el proveedor JSON, la conexión a BD por petición, los manejadores de error y todos los
    módulos de `app/modules/`; sirve `index.html` en `/` y, salvo `SKIP_SEED`, ejecuta la semilla de usuarios.

    Args:
        config: dict opcional que sobrescribe `Config` (p. ej. `{"SKIP_SEED": True}` en pruebas).

    Returns:
        La instancia de `Flask` lista para usarse.
    """
    app = Flask(__name__, static_folder="web", static_url_path="")
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    app.json = JSONProvider(app)
    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    excepciones.register(app)

    register_modules(app, f"{__name__}.modules")

    @app.get("/")
    def index():
        """Sirve el frontend (`index.html`) o 404 JSON si no está construido."""
        if not os.path.isfile(os.path.join(app.static_folder, "index.html")):
            return jsonify(error="Frontend no disponible."), 404
        return send_from_directory(app.static_folder, "index.html")

    if not app.config.get("SKIP_SEED"):
        from .seed import seed_if_empty

        try:
            seed_if_empty(app)
        except Exception:
            app.logger.exception("No se pudo ejecutar la semilla de usuarios (¿BD lista?)")
    return app
