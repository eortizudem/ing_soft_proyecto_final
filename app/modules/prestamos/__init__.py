"""Módulo prestamos: registro de la blueprint Flask (capa controller en `controller.py`).

Agrupa préstamos, renovaciones, devoluciones, recibos y políticas de préstamo.
"""
from app.core.module import make_blueprint

bp = make_blueprint(__name__)
