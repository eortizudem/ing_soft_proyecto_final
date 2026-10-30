"""Calendario de dias habiles (D-03): habil = lunes a viernes; los festivos cuentan como habiles.

Funciones puras, sin acceso a BD. Convencion: el dia `desde` no se cuenta; el dia 1 es el siguiente dia habil.
Se cumple siempre `habiles_entre(d, sumar_habiles(d, n)) == n`.
"""
from datetime import date, datetime, timedelta


def _d(x):
    """Normaliza datetime a date."""
    return x.date() if isinstance(x, datetime) else x


def es_habil(d: date) -> bool:
    """Lunes a viernes."""
    return _d(d).weekday() < 5


def sumar_habiles(desde: date, n: int) -> date:
    """Fecha tras `n` dias habiles posteriores a `desde` (n >= 0; n=0 devuelve `desde`).

    Prestamo en viernes con 5 dias -> el viernes siguiente; prestamo en sabado/domingo cuenta desde el lunes
    (el lunes es el dia 1).
    """
    if n < 0:
        raise ValueError("n debe ser >= 0")
    d = _d(desde)
    while n:
        d += timedelta(days=1)
        if es_habil(d):
            n -= 1
    return d


def habiles_entre(desde: date, hasta: date) -> int:
    """Dias habiles en el intervalo (desde, hasta]; 0 si hasta <= desde."""
    d, h = _d(desde), _d(hasta)
    if h <= d:
        return 0
    dias = (h - d).days
    completas, resto = divmod(dias, 7)
    total = completas * 5
    for i in range(1, resto + 1):
        if es_habil(d + timedelta(days=completas * 7 + i)):
            total += 1
    return total
