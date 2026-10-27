import logging
import os

from flask import Flask, jsonify, send_from_directory

from .config import Config
from .core import db, errors
from .core.module import register_modules
from .core.serializers import JSONProvider


def create_app(config=None):
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
