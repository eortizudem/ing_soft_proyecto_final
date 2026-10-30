"""Módulo `usuarios`: blueprint Flask de gestión de cuentas (RF-01, RF-03, RF-04). Capa: registro del módulo MVC."""

from app.core.module import make_blueprint

bp = make_blueprint(__name__)
