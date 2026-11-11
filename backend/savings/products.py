"""
Productos de ahorro simulados al estilo del mercado colombiano.
Tasas expresadas como Efectiva Anual (E.A.), la convención de los bancos en Colombia.
"""
from decimal import Decimal

PRODUCTS = {
    "AHORRO": {
        "code": "AHORRO", "name": "Cuenta de ahorro", "rate_ea": Decimal("0.035"), "term_days": None,
        "min_amount": Decimal("10"),
        "description": "Disponible en cualquier momento. Puedes aportar y retirar cuando quieras. Rentabilidad baja a cambio de liquidez total.",
    },
    "CDT90": {
        "code": "CDT90", "name": "CDT a 90 días", "rate_ea": Decimal("0.088"), "term_days": 90,
        "min_amount": Decimal("500"),
        "description": "Certificado de Depósito a Término. El dinero queda inmovilizado 90 días a cambio de una tasa mayor.",
    },
    "CDT180": {
        "code": "CDT180", "name": "CDT a 180 días", "rate_ea": Decimal("0.092"), "term_days": 180,
        "min_amount": Decimal("500"),
        "description": "Plazo de seis meses. Mayor tasa, menor liquidez.",
    },
    "CDT360": {
        "code": "CDT360", "name": "CDT a 360 días", "rate_ea": Decimal("0.096"), "term_days": 360,
        "min_amount": Decimal("500"),
        "description": "Plazo de un año. La tasa más alta de los productos de ahorro del simulador.",
    },
}
