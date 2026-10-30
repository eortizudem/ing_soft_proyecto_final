"""Pruebas de dias habiles (D-03): `es_habil`, `sumar_habiles` y `habiles_entre`."""
from datetime import date, datetime, timedelta

import pytest

from app.core.calendario import es_habil, habiles_entre, sumar_habiles

LUN, VIE, SAB, DOM = date(2026, 10, 26), date(2026, 10, 30), date(2026, 10, 31), date(2026, 11, 1)


def test_es_habil():
    """Lunes a viernes son habiles, sabado y domingo no; acepta datetime."""
    assert [es_habil(LUN + timedelta(days=i)) for i in range(7)] == [True] * 5 + [False] * 2
    assert es_habil(datetime(2026, 10, 26, 18, 0))


def test_sumar_habiles():
    """Suma dias habiles saltando fines de semana; n=0 devuelve la misma fecha y n negativo lanza ValueError."""
    assert sumar_habiles(LUN, 0) == LUN
    assert sumar_habiles(LUN, 4) == VIE
    assert sumar_habiles(LUN, 5) == date(2026, 11, 2)          # salta el fin de semana
    assert sumar_habiles(VIE, 1) == date(2026, 11, 2)
    assert sumar_habiles(VIE, 5) == date(2026, 11, 6)
    assert sumar_habiles(SAB, 5) == date(2026, 11, 6)          # sabado: el lunes es el dia 1
    assert sumar_habiles(DOM, 1) == date(2026, 11, 2)
    assert sumar_habiles(LUN, 10) == date(2026, 11, 9)
    assert sumar_habiles(datetime(2026, 10, 26, 9, 30), 1) == date(2026, 10, 27)
    with pytest.raises(ValueError):
        sumar_habiles(LUN, -1)


def test_habiles_entre():
    """Cuenta dias habiles en (desde, hasta] y devuelve 0 si hasta <= desde."""
    assert habiles_entre(LUN, LUN) == 0 and habiles_entre(VIE, LUN) == 0
    assert habiles_entre(LUN, VIE) == 4
    assert habiles_entre(VIE, date(2026, 11, 2)) == 1          # vence viernes, devuelve lunes: 1 dia
    assert habiles_entre(VIE, SAB) == 0 and habiles_entre(VIE, DOM) == 0
    assert habiles_entre(SAB, date(2026, 11, 2)) == 1
    assert habiles_entre(LUN, date(2026, 11, 9)) == 10


def test_roundtrip_exhaustivo():
    """`habiles_entre(d, sumar_habiles(d, n)) == n` para cualquier dia de inicio y n."""
    for i in range(14):
        d = LUN + timedelta(days=i)
        for n in range(0, 25):
            assert habiles_entre(d, sumar_habiles(d, n)) == n
