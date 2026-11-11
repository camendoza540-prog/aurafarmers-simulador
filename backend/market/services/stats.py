"""Estadísticas y análisis de tendencia de un instrumento a partir de su historia diaria."""
import math
from datetime import timedelta

import numpy as np
from django.conf import settings

from market.models import Instrument

RANGES = {"1M": 31, "3M": 92, "6M": 183, "1A": 365, "2A": 730, "MAX": 3650}


def closes_series(inst: Instrument, days: int | None = None):
    qs = inst.bars.order_by("date")
    if days:
        last = qs.last()
        if last:
            qs = qs.filter(date__gte=last.date - timedelta(days=days))
    rows = list(qs.values_list("date", "close"))
    dates = [r[0] for r in rows]
    closes = np.array([float(r[1]) for r in rows], dtype=float)
    return dates, closes


def sma(values: np.ndarray, window: int):
    out = np.full(len(values), np.nan)
    if len(values) >= window:
        c = np.cumsum(np.insert(values, 0, 0.0))
        out[window - 1:] = (c[window:] - c[:-window]) / window
    return out


def rsi(values: np.ndarray, period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    delta = np.diff(values)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_g = gains[:period].mean()
    avg_l = losses[:period].mean()
    for g, l in zip(gains[period:], losses[period:]):
        avg_g = (avg_g * (period - 1) + g) / period
        avg_l = (avg_l * (period - 1) + l) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return float(100 - 100 / (1 + rs))


def max_drawdown(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    peaks = np.maximum.accumulate(values)
    dd = values / peaks - 1
    return float(dd.min())


def _pct(a, b):
    if b is None or b == 0 or a is None:
        return None
    return round((a / b - 1) * 100, 2)


def _clean(x, nd=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), nd)


def aligned_returns(instruments, days=365):
    """Matriz de rendimientos diarios alineados por fecha (filas = días, columnas = instrumentos)."""
    series = {}
    common = None
    for inst in instruments:
        dates, closes = closes_series(inst, days)
        series[inst.symbol] = dict(zip(dates, closes))
        common = set(dates) if common is None else common & set(dates)
    common = sorted(common or [])
    if len(common) < 3:
        return common, np.zeros((0, len(instruments)))
    prices = np.array([[series[i.symbol][d] for i in instruments] for d in common])
    rets = prices[1:] / prices[:-1] - 1
    return common, rets


def instrument_stats(inst: Instrument) -> dict:
    from market.catalog import BENCHMARK_SYMBOL

    dates, closes = closes_series(inst)
    price = float(inst.current_price)
    if len(closes) == 0:
        return {}
    rf = settings.SIMULATION["RISK_FREE_RATE"]
    last_date = dates[-1]

    def close_n_days_ago(n):
        target = last_date - timedelta(days=n)
        idx = next((i for i in range(len(dates) - 1, -1, -1) if dates[i] <= target), None)
        return float(closes[idx]) if idx is not None else None

    ytd_idx = next((i for i, d in enumerate(dates) if d.year == last_date.year), None)
    ytd_base = float(closes[ytd_idx - 1]) if ytd_idx and ytd_idx > 0 else (float(closes[0]) if ytd_idx == 0 else None)

    one_year = closes[-253:] if len(closes) > 253 else closes
    rets = np.diff(np.log(one_year)) if len(one_year) > 1 else np.array([0.0])
    vol = float(rets.std(ddof=1) * math.sqrt(252)) if len(rets) > 2 else 0.0
    ann_ret = (one_year[-1] / one_year[0]) ** (252 / max(len(one_year) - 1, 1)) - 1
    sharpe = (ann_ret - rf) / vol if vol else None

    s20, s50, s200 = sma(closes, 20)[-1], sma(closes, 50)[-1], sma(closes, 200)[-1]
    if not math.isnan(s50) and not math.isnan(s200):
        if price > s50 > s200:
            trend, trend_text = "alcista", "El precio está por encima de sus promedios de 50 y 200 días: tendencia alcista."
        elif price < s50 < s200:
            trend, trend_text = "bajista", "El precio está por debajo de sus promedios de 50 y 200 días: tendencia bajista."
        else:
            trend, trend_text = "lateral", "Los promedios móviles se cruzan: el mercado no muestra una dirección clara."
    else:
        trend, trend_text = "lateral", "No hay suficiente historia para determinar una tendencia."

    beta = None
    if inst.symbol != BENCHMARK_SYMBOL:
        bench = Instrument.objects.filter(symbol=BENCHMARK_SYMBOL).first()
        if bench:
            _, mat = aligned_returns([inst, bench], 365)
            if len(mat) > 20:
                cov = np.cov(mat[:, 0], mat[:, 1])
                beta = cov[0, 1] / cov[1, 1] if cov[1, 1] else None
    else:
        beta = 1.0

    r14 = rsi(closes[-120:])
    if r14 is None:
        rsi_text = None
    elif r14 >= 70:
        rsi_text = "Sobrecompra: subió mucho en poco tiempo; podría corregir."
    elif r14 <= 30:
        rsi_text = "Sobreventa: cayó mucho en poco tiempo; podría rebotar."
    else:
        rsi_text = "Zona neutral."

    return {
        "price": _clean(price, 4),
        "returns": {
            "1D": _clean(inst.change_pct),
            "1M": _pct(price, close_n_days_ago(30)),
            "3M": _pct(price, close_n_days_ago(91)),
            "6M": _pct(price, close_n_days_ago(182)),
            "YTD": _pct(price, ytd_base),
            "1A": _pct(price, close_n_days_ago(365)),
        },
        "volatility_annual": _clean(vol * 100),
        "annual_return_1y": _clean(ann_ret * 100),
        "sharpe": _clean(sharpe),
        "max_drawdown_1y": _clean(max_drawdown(one_year) * 100),
        "high_52w": _clean(float(one_year.max()), 4),
        "low_52w": _clean(float(one_year.min()), 4),
        "sma20": _clean(s20, 4),
        "sma50": _clean(s50, 4),
        "sma200": _clean(s200, 4),
        "rsi14": _clean(r14, 1),
        "rsi_text": rsi_text,
        "beta": _clean(beta),
        "trend": trend,
        "trend_text": trend_text,
        "risk_level": "alto" if vol > 0.35 else ("medio" if vol > 0.18 else "bajo"),
    }


def history_payload(inst: Instrument, range_key: str = "1A"):
    days = RANGES.get(range_key, 365)
    dates, closes = closes_series(inst)  # historia completa para que los promedios sean correctos
    s20, s50 = sma(closes, 20), sma(closes, 50)
    bars = list(inst.bars.order_by("date").values("date", "open", "high", "low", "close", "volume"))
    if not bars:
        return []
    cutoff = bars[-1]["date"] - timedelta(days=days)
    out = []
    for i, b in enumerate(bars):
        if b["date"] < cutoff:
            continue
        out.append({
            "date": b["date"].isoformat(),
            "open": float(b["open"]), "high": float(b["high"]), "low": float(b["low"]),
            "close": float(b["close"]), "volume": b["volume"],
            "sma20": _clean(s20[i], 4) if i < len(s20) else None,
            "sma50": _clean(s50[i], 4) if i < len(s50) else None,
        })
    return out


def sparkline(inst: Instrument, points: int = 30):
    """Minigráfica de 30 días (en caché 60 s: la lista del mercado la pide para 66 activos)."""
    from django.core.cache import cache

    key = f"spark:{inst.symbol}:{points}"
    data = cache.get(key)
    if data is None:
        closes = list(inst.bars.order_by("-date").values_list("close", flat=True)[:points])
        data = [round(float(c), 4) for c in reversed(closes)]
        cache.set(key, data, 60)
    if data:
        data = data[:-1] + [round(float(inst.current_price), 4)]  # el último punto, siempre en vivo
    return data
