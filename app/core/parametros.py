"""Parametros de negocio configurables por entorno (app/config.py). Leen current_app o, sin contexto, Config."""
from decimal import Decimal

from flask import current_app, has_app_context

from ..config import Config


def _get(nombre):
    """Valor del parametro: `current_app.config` si hay contexto de app; si no, el valor de `Config`."""
    return current_app.config.get(nombre, getattr(Config, nombre)) if has_app_context() else getattr(Config, nombre)


def tipo_cambio() -> Decimal:
    """USD -> MXN (D-07)."""
    return Decimal(str(_get("TIPO_CAMBIO_USD_MXN")))


def presupuesto_mensual() -> Decimal:
    """Presupuesto mensual de compras en USD (D-22)."""
    return Decimal(str(_get("PRESUPUESTO_MENSUAL_USD")))


def dias_reserva_espera() -> int:
    """Dias habiles que se aparta un ejemplar al notificar a quien espera (D-19)."""
    return int(_get("ESPERA_DIAS_RESERVA"))
