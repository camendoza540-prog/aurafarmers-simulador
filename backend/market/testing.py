"""Utilidades compartidas por las pruebas automáticas."""
from decimal import Decimal

from market.catalog import INSTRUMENTS
from market.models import Instrument
from market.services.engine import generate_history


def make_instruments(symbols=("SPY", "AAPL", "KO", "AGG", "TLT", "GLD")):
    out = {}
    for spec in INSTRUMENTS:
        if spec["symbol"] not in symbols:
            continue
        inst = Instrument.objects.create(
            symbol=spec["symbol"], name=spec["name"], type=spec["type"], sector=spec["sector"],
            asset_class=spec.get("asset_class", "equity"), anchor_price=Decimal(str(spec["anchor"])),
            annual_drift=spec["mu"], annual_volatility=spec["sigma"], beta=spec.get("beta", 1.0),
            duration=spec.get("duration", 0.0),
            base_currency=spec.get("base", ""), quote_currency=spec.get("quote", "USD"),
            leverage_cap=spec.get("cap"), spread=spec.get("spread"),
        )
        generate_history(inst, years=1)
        out[inst.symbol] = inst
    return out
