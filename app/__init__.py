"""Fabrica de la aplicacion Flask: configuracion, BD, errores, modulos MVC y semilla inicial."""
import logging
import os

from flask import Flask, jsonify, send_from_directory

from .config import Config
from .core import db, errors
from .core.module import register_modules
from .core.serializers import JSONProvider


def create_app(config=None):
    """Construye y configura la aplicacion Flask.

    Carga `Config`, registra el proveedor JSON, la conexion a BD por peticion, los manejadores de error y todos los
    modulos de `app/modules/`; sirve `index.html` en `/` y, salvo `SKIP_SEED`, ejecuta la semilla de usuarios.

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
    errors.register(app)

    register_modules(app, f"{__name__}.modules")

    @app.get("/")
    def index():
        """Sirve el frontend (`index.html`) o 404 JSON si no esta construido."""
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
