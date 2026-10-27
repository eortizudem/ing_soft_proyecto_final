"""Registro de modulos: cada app/modules/<m>/__init__.py solo declara `bp = make_blueprint(__name__)`."""
import importlib
import os

from flask import Blueprint


def make_blueprint(import_name):
    """Blueprint con nombre del modulo y estaticos del frontend en /m/<modulo>."""
    name = import_name.rsplit(".", 1)[-1]
    return Blueprint(name, import_name, static_folder="web", static_url_path=f"/m/{name}")


def register_modules(app, package):
    """Importa cada subpaquete de `package` con __init__.py (+ su controller) y registra su `bp`."""
    mod = importlib.import_module(package)
    base = next(iter(mod.__path__))
    for name in sorted(os.listdir(base)):
        if os.path.isfile(os.path.join(base, name, "__init__.py")):
            m = importlib.import_module(f"{package}.{name}")
            if os.path.isfile(os.path.join(base, name, "controller.py")):
                importlib.import_module(f"{package}.{name}.controller")
            app.register_blueprint(m.bp)
