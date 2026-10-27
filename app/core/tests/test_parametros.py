from decimal import Decimal

from app.core import parametros


def test_defaults_con_contexto(app):
    with app.app_context():
        assert parametros.tipo_cambio() == Decimal("18.00")
        assert parametros.presupuesto_mensual() == Decimal("5000")
        assert parametros.dias_reserva_espera() == 2


def test_sobrescritura_por_config(app):
    app.config.update(TIPO_CAMBIO_USD_MXN="17.5", PRESUPUESTO_MENSUAL_USD=1200, ESPERA_DIAS_RESERVA="3")
    try:
        with app.app_context():
            assert parametros.tipo_cambio() == Decimal("17.5")
            assert parametros.presupuesto_mensual() == Decimal("1200")
            assert parametros.dias_reserva_espera() == 3
    finally:
        for k in ("TIPO_CAMBIO_USD_MXN", "PRESUPUESTO_MENSUAL_USD", "ESPERA_DIAS_RESERVA"):
            app.config.pop(k)
    with app.app_context():
        assert parametros.tipo_cambio() == Decimal("18.00")


def test_sin_contexto_usa_config():
    assert isinstance(parametros.tipo_cambio(), Decimal)
