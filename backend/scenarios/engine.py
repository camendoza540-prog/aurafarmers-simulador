"""
Simulación Monte Carlo de un portafolio bajo un escenario de mercado.

Para cada activo i y día t:
    r_i,t = (μ_i + Δμ − σ_i'²/2)·dt + β_i·σ_m'·√dt·Z_m,t + σ_idio_i'·√dt·Z_i,t + choque_i,t + recuperación_i,t

  · σ' = σ × multiplicador de volatilidad
  · El choque se reparte en los primeros `shock_days` días y depende del tipo de activo:
      acciones/ETF de acciones: β·choque − 2·Δtasa
      renta fija:               −duración·Δtasa (+ refugio si hay crisis)
      oro:                      −0,25·choque (suele subir en crisis)
      inmobiliario:             β·choque − 4·Δtasa
  · La recuperación devuelve un % de la caída durante el resto del horizonte.
  · El efectivo crece a la tasa libre de riesgo + Δtasa.
"""
import math

import numpy as np
from django.conf import settings

from market.models import Instrument

N_PATHS = 1000
MAX_POINTS = 120


def asset_shock(inst: Instrument, shock: float, d_rate: float) -> float:
    if inst.asset_class == "bond":
        s = -inst.duration * d_rate + (0.08 * -shock if shock < 0 else 0)
    elif inst.asset_class == "commodity" and inst.beta < 0.2:
        s = -0.25 * shock          # oro: refugio, suele subir en crisis
    elif inst.asset_class in ("commodity", "forex", "crypto"):
        s = inst.beta * shock      # petróleo, cripto; USDCOP sube (beta negativa) en crisis
    elif inst.asset_class == "real_estate":
        s = inst.beta * shock - 4 * d_rate
    else:
        s = inst.beta * shock - 2 * d_rate
    return max(s, -0.95)


MAX_SIGMA = 1.2          # tope de volatilidad anual por activo, aun con el multiplicador
VOL_HALF_LIFE = 63       # días hábiles en que la volatilidad extra se reduce a la mitad tras el choque


def _vol_profile(p, horizon):
    """Multiplicador de volatilidad por día: elevado durante el choque y decae después.
    Sin choque, el multiplicador se aplica en todo el horizonte (régimen de volatilidad)."""
    vm = p["volatility_multiplier"]
    days = np.arange(horizon)
    shock_days = int(p["shock_days"]) if p["market_shock"] or p["rate_change"] else 0
    if vm == 1 or shock_days == 0:
        return np.full(horizon, vm)
    after = np.maximum(days - shock_days, 0)
    return 1 + (vm - 1) * np.power(0.5, after / VOL_HALF_LIFE)


def _asset_log_paths(insts, p, rng):
    """Matriz de log-precios relativos por instrumento: {símbolo: (N_PATHS × horizon+1)}."""
    horizon = p["horizon_days"]
    dt = 1 / 252
    vprof = _vol_profile(p, horizon)                       # (horizon,)
    sm_base = settings.SIMULATION["MARKET_VOLATILITY"]
    zm = rng.standard_normal((N_PATHS, horizon))
    shock = p["market_shock"] / 100
    d_rate = p["rate_change"] / 100
    drift_adj = p["drift_adjustment"] / 100
    shock_days = max(int(p["shock_days"]), 1) if shock or d_rate else 0
    shock_days = min(shock_days, horizon)
    recovery = p["recovery"] / 100

    out, shocks = {}, {}
    for inst in insts:
        sigma = np.minimum(inst.annual_volatility * vprof, MAX_SIGMA)        # (horizon,)
        sm = sm_base * vprof
        idio = np.sqrt(np.maximum(sigma ** 2 - (inst.beta ** 2) * sm ** 2, (0.25 * sigma) ** 2))
        zi = rng.standard_normal((N_PATHS, horizon))
        mu = inst.annual_drift + drift_adj + (d_rate * 0.5 if inst.asset_class == "bond" else 0)
        r = (mu - 0.5 * sigma ** 2) * dt + inst.beta * sm * math.sqrt(dt) * zm + idio * math.sqrt(dt) * zi
        s_i = asset_shock(inst, shock, d_rate) if shock_days else 0.0
        if shock_days:
            log_shock = math.log1p(s_i)
            r[:, :shock_days] += log_shock / shock_days
            if recovery and s_i < 0 and horizon > shock_days:
                r[:, shock_days:] += (-log_shock * recovery) / (horizon - shock_days)
        out[inst.symbol] = np.concatenate([np.zeros((N_PATHS, 1)), np.cumsum(r, axis=1)], axis=1)
        shocks[inst.symbol] = s_i
    return out, shocks


def _simulate_paths(holdings, cfds, cash, p, rng_seed):
    """
    holdings: [(inst, valor)] de contado · cfds: [(inst, dirección, nocional, capital_actual, margen)]
    Devuelve la matriz (N_PATHS × horizon+1) del valor total y el detalle por activo.
    """
    horizon = p["horizon_days"]
    rng = np.random.default_rng(rng_seed)
    insts = {i.symbol: i for i, *_ in holdings + cfds}
    logs, shocks = _asset_log_paths(list(insts.values()), p, rng)

    total = np.zeros((N_PATHS, horizon + 1))
    per_asset = {}

    def _acc(inst, kind, initial, path):
        row = per_asset.setdefault(inst.symbol + kind, {
            "symbol": inst.symbol, "name": inst.name, "kind": kind,
            "asset_class": inst.get_asset_class_display(), "initial_value": 0.0,
            "shock_pct": round(shocks[inst.symbol] * 100, 2), "_final": np.zeros(N_PATHS),
        })
        row["initial_value"] += initial
        row["_final"] += path[:, -1]

    for inst, value in holdings:
        path = value * np.exp(logs[inst.symbol])
        total += path
        _acc(inst, "Contado", value, path)

    for inst, direction, notional, equity_now, margin in cfds:
        rel = np.exp(logs[inst.symbol]) - 1
        path = equity_now + direction * notional * rel
        # Cierre forzoso: si el capital de la posición cae a la mitad del margen, queda congelado ahí
        stop = 0.5 * margin
        hit = path <= stop
        any_hit = hit.any(axis=1)
        first = np.argmax(hit, axis=1)
        for k in np.where(any_hit)[0]:
            path[k, first[k]:] = max(path[k, first[k]], 0.0)
        path = np.maximum(path, 0.0)
        total += path
        _acc(inst, "CFD 1:{}".format(int(round(notional / margin))) if margin else "CFD", equity_now, path)

    cash_rate = settings.SIMULATION["RISK_FREE_RATE"] + p["rate_change"] / 100
    total += cash * (1 + max(cash_rate, 0)) ** (np.arange(horizon + 1) / 252)

    rows = []
    for row in per_asset.values():
        final = row.pop("_final")
        med = float(np.median(final))
        row["initial_value"] = round(row["initial_value"], 2)
        row["median_final"] = round(med, 2)
        row["median_return_pct"] = round((med / row["initial_value"] - 1) * 100, 2) if row["initial_value"] else 0.0
        rows.append(row)
    rows.sort(key=lambda r: r["initial_value"], reverse=True)
    return total, rows


def run_simulation(portfolio, valuation, params: dict, seed: int = 2026) -> dict:
    params = dict(params)
    horizon = params["horizon_days"]
    params["shock_days"] = min(int(params["shock_days"]), horizon)
    hold = [h for h in valuation["holdings"] if h["market_value"] > 0]
    insts = {i.symbol: i for i in Instrument.objects.filter(symbol__in=[h["symbol"] for h in hold])}
    holdings = [(insts[h["symbol"]], float(h["market_value"])) for h in hold]
    cfds = []
    for pos in portfolio.positions.filter(status="OPEN").select_related("instrument"):
        equity_now = float(pos.margin + pos.unrealized_pnl())
        inst = pos.instrument
        notional_usd = float(pos.quantity * inst.current_price * inst.usd_factor())
        cfds.append((inst, pos.direction, notional_usd, max(equity_now, 0.0), float(pos.margin)))
    cash = float(valuation["cash"])
    initial = cash + sum(v for _, v in holdings) + sum(c[3] for c in cfds)

    paths, per_asset = _simulate_paths(holdings, cfds, cash, params, seed)
    base_params = {**params, "market_shock": 0, "shock_days": 0, "recovery": 0, "volatility_multiplier": 1.0,
                   "rate_change": 0, "drift_adjustment": 0}
    base_paths, _ = _simulate_paths(holdings, cfds, cash, base_params, seed)

    idx = np.unique(np.linspace(0, horizon, min(MAX_POINTS, horizon + 1)).astype(int))
    pct = np.percentile(paths[:, idx], [5, 25, 50, 75, 95], axis=0)
    base_med = np.median(base_paths[:, idx], axis=0)
    bands = [{
        "day": int(d),
        "p5": round(float(pct[0, k]), 2), "p25": round(float(pct[1, k]), 2),
        "p50": round(float(pct[2, k]), 2), "p75": round(float(pct[3, k]), 2),
        "p95": round(float(pct[4, k]), 2), "baseline": round(float(base_med[k]), 2),
        "band_outer": [round(float(pct[0, k]), 2), round(float(pct[4, k]), 2)],
        "band_inner": [round(float(pct[1, k]), 2), round(float(pct[3, k]), 2)],
    } for k, d in enumerate(idx)]

    final = paths[:, -1]
    rets = (final / initial - 1) * 100
    p5 = float(np.percentile(final, 5))
    tail = final[final <= p5]
    peaks = np.maximum.accumulate(paths, axis=1)
    mdd = ((paths / np.where(peaks > 0, peaks, 1)) - 1).min(axis=1)
    lo, hi = np.percentile(rets, [1, 99])
    if hi - lo < 1e-6:
        hi = lo + 1
    counts, edges = np.histogram(np.clip(rets, lo, hi), bins=24, range=(lo, hi))
    med_path = np.median(paths, axis=0)
    worst_day_idx = int(np.argmin(med_path))

    summary = {
        "initial_value": round(initial, 2),
        "expected_final": round(float(final.mean()), 2),
        "median_final": round(float(np.median(final)), 2),
        "baseline_median_final": round(float(np.median(base_paths[:, -1])), 2),
        "expected_return_pct": round(float(rets.mean()), 2),
        "median_return_pct": round(float(np.median(rets)), 2),
        "prob_loss": round(float((final < initial).mean() * 100), 1),
        "prob_loss_20": round(float((rets < -20).mean() * 100), 1),
        "best_case": round(float(np.percentile(final, 95)), 2),
        "worst_case": round(p5, 2),
        "var95": round(max(initial - p5, 0), 2),
        "cvar95": round(max(initial - float(tail.mean()), 0), 2) if len(tail) else None,
        "median_max_drawdown_pct": round(float(np.median(mdd)) * 100, 2),
        "worst_point_day": worst_day_idx,
        "worst_point_value": round(float(med_path[worst_day_idx]), 2),
        "paths": N_PATHS,
        "horizon_days": horizon,
        "has_leverage": bool(cfds),
    }
    histogram = [{"from": round(float(edges[i]), 1), "to": round(float(edges[i + 1]), 1),
                  "mid": round(float((edges[i] + edges[i + 1]) / 2), 1), "count": int(c)} for i, c in enumerate(counts)]
    return {"summary": summary, "bands": bands, "histogram": histogram, "assets": per_asset,
            "explanation": explain(summary, params)}


def _n(x, nd=0) -> str:
    """Número con formato colombiano: punto de miles y coma decimal."""
    txt = f"{x:,.{nd}f}"
    return txt.replace(",", "§").replace(".", ",").replace("§", ".")


def _pct(x, nd=1, signed=False) -> str:
    sign = "+" if signed and x > 0 else ("−" if x < 0 else "")
    return f"{sign}{_n(abs(x), nd)} %"


def explain(s, p) -> list[str]:
    out = []
    days = p["horizon_days"]
    years = days / 252
    horizon_txt = f"{days} días hábiles (≈ {_n(years, 1)} años)" if years >= 1 else f"{days} días hábiles (≈ {_n(days / 21)} meses)"
    out.append(f"Se simularon {_n(s['paths'])} futuros posibles de tu portafolio durante {horizon_txt}.")
    out.append(
        f"En el caso típico (mediana) terminarías con US$ {_n(s['median_final'])}, "
        f"un {_pct(s['median_return_pct'], signed=True)}. Sin el escenario, la mediana sería US$ {_n(s['baseline_median_final'])}."
    )
    out.append(
        f"La probabilidad de terminar con pérdidas es {_pct(s['prob_loss'])}; "
        f"la de perder más del 20 %, {_pct(s['prob_loss_20'])}."
    )
    out.append(
        f"En el 5 % de los peores casos perderías al menos US$ {_n(s['var95'])} (VaR 95 %). "
        f"La caída máxima típica desde un pico es {_pct(abs(s['median_max_drawdown_pct']))}."
    )
    if p["market_shock"] < 0 and p["recovery"] < 50:
        out.append("Con poca recuperación, el horizonte de inversión importa: quien vende en el fondo de la caída convierte la pérdida temporal en definitiva.")
    if s.get("has_leverage"):
        out.append("Incluye tus posiciones CFD apalancadas: amplifican el resultado y pueden cerrarse por margen si caen a la mitad del margen.")
    if p["volatility_multiplier"] > 1 and p["shock_days"]:
        out.append("La volatilidad sube durante el choque y vuelve gradualmente a la normalidad después (vida media de unos 3 meses).")
    if p["rate_change"] > 0:
        out.append("Al subir las tasas, los bonos de larga duración (como TLT) pierden valor; el efectivo y los CDT, en cambio, rinden más.")
    return out
