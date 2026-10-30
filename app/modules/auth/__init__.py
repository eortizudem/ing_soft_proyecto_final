"""Modulo `auth`: autenticacion, acceso de visitante y recuperacion de contrasena (RNF-01, D-26). Registra el blueprint del modulo."""
from app.core.module import make_blueprint

bp = make_blueprint(__name__)
