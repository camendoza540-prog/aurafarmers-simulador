"""
Lógica de negocio de portafolios: compra/venta, aportes, valoración, métricas de riesgo,
retroalimentación y backtest. Toda operación de dinero usa Decimal y transacciones atómicas.
"""
import math
from datetime import timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

import numpy as np
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from market.catalog import BENCHMARK_SYMBOL
from market.models import Instrument, PriceBar
from market.services.engine import tick
from market.services.stats import aligned_returns, max_drawdown
from users.models import InsufficientFunds

from .models import Holding, Portfolio, PortfolioSnapshot, Transaction
from config.formatting import usd

Q2, Q4, Q6 = Decimal("0.01"), Decimal("0.0001"), Decimal("0.000001")
ZERO = Decimal("0")
SNAPSHOT_EVERY_SECONDS = 60


class TradeError(Exception):
    """Error de negocio mostrado al usuario."""


def _commission(gross: Decimal) -> Decimal:
    cfg = settings.SIMULATION
    return max((gross * cfg["COMMISSION_RATE"]).quantize(Q2, ROUND_HALF_UP), cfg["MIN_COMMISSION"])


# ── Gestión de portafolios ────────────────────────────────────────────────

@transaction.atomic
def create_portfolio(user, name, initial_deposit: Decimal, description="", color="pine") -> Portfolio:
    name = (name or "").strip()
    if not name:
        raise TradeError("El portafolio necesita un nombre.")
    if Portfolio.objects.filter(user=user, name__iexact=name).exists():
        raise TradeError("Ya tienes un portafolio con ese nombre.")
    if user.portfolios.count() >= 10:
        raise TradeError("Puedes tener máximo 10 portafolios.")
    p = Portfolio.objects.create(user=user, name=name, description=description, color=color)
    if initial_deposit and initial_deposit > 0:
        deposit(p, initial_deposit)
    else:
        record_snapshot(p, force=True)
    return p


@transaction.atomic
def deposit(portfolio: Portfolio, amount: Decimal) -> Transaction:
    amount = Decimal(amount).quantize(Q2)
    if amount <= 0:
        raise TradeError("El monto debe ser mayor que cero.")
    try:
        portfolio.user.profile.debit(amount)
    except InsufficientFunds as exc:
        raise TradeError(str(exc)) from exc
    portfolio.cash += amount
    portfolio.net_contributions += amount
    portfolio.save(update_fields=["cash", "net_contributions", "updated_at"])
    tx = Transaction.objects.create(portfolio=portfolio, type="DEPOSIT", total=amount, cash_after=portfolio.cash)
    record_snapshot(portfolio, force=True)
    return tx


@transaction.atomic
def withdraw(portfolio: Portfolio, amount: Decimal) -> Transaction:
    amount = Decimal(amount).quantize(Q2)
    if amount <= 0:
        raise TradeError("El monto debe ser mayor que cero.")
    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
    from .trading import margin_status
    m = margin_status(portfolio)
    # Con posiciones CFD abiertas solo se retira el margen libre (como en un bróker real)
    available = min(portfolio.cash, m["free_margin"]) if m["open_positions"] else portfolio.cash
    if amount > available:
        if m["open_positions"]:
            raise TradeError(f"Puedes retirar hasta {usd(available)}: el resto respalda tus posiciones con margen. Cierra posiciones para liberar más.")
        raise TradeError(f"El portafolio solo tiene {usd(portfolio.cash)} en efectivo. Vende posiciones primero.")
    portfolio.cash -= amount
    portfolio.net_contributions -= amount
    portfolio.save(update_fields=["cash", "net_contributions", "updated_at"])
    portfolio.user.profile.credit(amount)
    tx = Transaction.objects.create(portfolio=portfolio, type="WITHDRAW", total=amount, cash_after=portfolio.cash)
    record_snapshot(portfolio, force=True)
    return tx


@transaction.atomic
def close_portfolio(portfolio: Portfolio) -> Decimal:
    """Liquida todas las posiciones a precio de mercado y devuelve el efectivo a la cuenta principal."""
    from .trading import close_position
    for pos in list(portfolio.positions.filter(status="OPEN")):
        close_position(pos, "PORTFOLIO")
    for h in list(portfolio.holdings.select_related("instrument")):
        execute_trade(portfolio, h.instrument.symbol, "SELL", quantity=h.quantity)
    portfolio.refresh_from_db()
    returned = portfolio.cash
    portfolio.user.profile.credit(returned)
    portfolio.delete()
    return returned


# ── Operaciones de compra y venta ─────────────────────────────────────────

@transaction.atomic
def execute_trade(portfolio: Portfolio, symbol: str, side: str, quantity=None, amount=None,
                  note: str = "", take_profit=None, stop_loss=None) -> Transaction:
    side = (side or "").upper()
    if side not in ("BUY", "SELL"):
        raise TradeError("Operación inválida: usa BUY o SELL.")
    try:
        inst = Instrument.objects.get(symbol=(symbol or "").upper(), is_active=True)
    except Instrument.DoesNotExist:
        raise TradeError("Instrumento no encontrado.")
    if inst.cfd_only and side == "BUY":
        raise TradeError(f"{inst.symbol} ({inst.get_type_display().lower()}) solo se opera como CFD con margen, no de contado.")
    tick(inst, check_orders=False)
    inst.refresh_from_db()
    price = inst.current_price
    if price <= 0:
        raise TradeError("El instrumento no tiene precio disponible.")
    if side == "BUY" and (take_profit not in (None, "") or stop_loss not in (None, "")):
        from .trading import TradingError, validate_protection
        try:
            take_profit, stop_loss = validate_protection("LONG", price, take_profit, stop_loss)
        except TradingError as exc:
            raise TradeError(str(exc))

    if amount not in (None, ""):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise TradeError("El monto debe ser mayor que cero.")
        if side == "BUY":
            # Se descuenta la comisión del monto para no exceder lo que el usuario quiere gastar
            fee_est = _commission(amount)
            quantity = ((amount - fee_est) / price).quantize(Q6, ROUND_DOWN)
        else:
            quantity = (amount / price).quantize(Q6, ROUND_DOWN)
    if quantity in (None, ""):
        raise TradeError("Indica una cantidad o un monto.")
    quantity = Decimal(str(quantity)).quantize(Q6, ROUND_DOWN)
    if quantity <= 0:
        raise TradeError("La cantidad debe ser mayor que cero.")

    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
    gross = (quantity * price).quantize(Q2, ROUND_HALF_UP)
    fee = _commission(gross)
    realized = None

    if side == "BUY":
        total = gross + fee
        if total > portfolio.cash:
            raise TradeError(
                f"Saldo insuficiente: la operación cuesta {usd(total)} (incluye comisión de {usd(fee)}) "
                f"y el portafolio tiene {usd(portfolio.cash)}."
            )
        holding, created = Holding.objects.select_for_update().get_or_create(
            portfolio=portfolio, instrument=inst, defaults={"quantity": ZERO, "avg_cost": ZERO}
        )
        new_qty = holding.quantity + quantity
        holding.avg_cost = ((holding.quantity * holding.avg_cost + gross + fee) / new_qty).quantize(Q4, ROUND_HALF_UP)
        holding.quantity = new_qty
        if take_profit is not None:
            holding.take_profit = take_profit
        if stop_loss is not None:
            holding.stop_loss = stop_loss
        holding.save()
        portfolio.cash -= total
    else:
        holding = Holding.objects.select_for_update().filter(portfolio=portfolio, instrument=inst).first()
        if not holding or holding.quantity <= 0:
            raise TradeError(f"No tienes {inst.symbol} en este portafolio.")
        if quantity > holding.quantity:
            if quantity - holding.quantity <= Decimal("0.0001"):
                quantity = holding.quantity
                gross = (quantity * price).quantize(Q2, ROUND_HALF_UP)
                fee = _commission(gross)
            else:
                raise TradeError(f"Solo tienes {holding.quantity.normalize()} unidades de {inst.symbol}.")
        if fee >= gross:
            raise TradeError("El monto de la venta no alcanza a cubrir la comisión mínima.")
        total = gross - fee
        realized = (total - quantity * holding.avg_cost).quantize(Q2, ROUND_HALF_UP)
        holding.quantity -= quantity
        if holding.quantity <= Decimal("0.000001"):
            holding.delete()
        else:
            holding.save()
        portfolio.cash += total

    portfolio.save(update_fields=["cash", "updated_at"])
    tx = Transaction.objects.create(
        portfolio=portfolio, instrument=inst, type=side, quantity=quantity, price=price,
        fee=fee, total=total, realized_pnl=realized, cash_after=portfolio.cash, note=note,
    )
    record_snapshot(portfolio, force=True)
    return tx


# ── Valoración ────────────────────────────────────────────────────────────

def valuate_portfolio(portfolio: Portfolio, record=True) -> dict:
    # El efectivo pudo cambiar en otra transacción (orden ejecutada, cierre forzoso): leer el vigente
    portfolio.refresh_from_db(fields=["cash", "net_contributions"])
    holdings = list(portfolio.holdings.select_related("instrument"))
    rows = []
    invested = cost = day_change = ZERO
    for h in holdings:
        inst = h.instrument
        mv = (h.quantity * inst.current_price).quantize(Q2)
        cb = (h.quantity * h.avg_cost).quantize(Q2)
        invested += mv
        cost += cb
        day_change += h.quantity * (inst.current_price - inst.previous_close)
        rows.append({
            "symbol": inst.symbol, "name": inst.name, "type": inst.type, "sector": inst.sector,
            "asset_class": inst.asset_class,
            "quantity": h.quantity, "avg_cost": h.avg_cost, "price": inst.current_price,
            "market_value": mv, "cost_basis": cb, "unrealized_pnl": mv - cb,
            "unrealized_pnl_pct": ((mv / cb - 1) * 100).quantize(Q2) if cb else ZERO,
            "day_change_pct": round(inst.change_pct, 2),
            "take_profit": h.take_profit, "stop_loss": h.stop_loss,
        })
    from .trading import margin_status
    margin = margin_status(portfolio)
    cfd_value = margin["margin_used"] + margin["unrealized_pnl"]
    total = (portfolio.cash + invested + cfd_value).quantize(Q2)
    for r in rows:
        r["weight"] = ((r["market_value"] / total) * 100).quantize(Q2) if total else ZERO
    rows.sort(key=lambda r: r["market_value"], reverse=True)

    realized = portfolio.transactions.filter(type__in=["SELL", "CFD_CLOSE"]).aggregate(s=Sum("realized_pnl"))["s"] or ZERO
    fees = portfolio.transactions.aggregate(s=Sum("fee"))["s"] or ZERO
    total_return = total - portfolio.net_contributions
    prev_total = total - day_change
    result = {
        "cash": portfolio.cash,
        "invested_value": invested.quantize(Q2),
        "cost_basis": cost.quantize(Q2),
        "total_value": total,
        "net_contributions": portfolio.net_contributions,
        "unrealized_pnl": (invested - cost).quantize(Q2),
        "realized_pnl": realized.quantize(Q2),
        "fees_paid": fees.quantize(Q2),
        "total_return": total_return.quantize(Q2),
        "total_return_pct": ((total_return / portfolio.net_contributions) * 100).quantize(Q2) if portfolio.net_contributions > 0 else ZERO,
        "day_change": day_change.quantize(Q2),
        "day_change_pct": ((day_change / prev_total) * 100).quantize(Q2) if prev_total > 0 else ZERO,
        "holdings": rows,
        "cfd_value": cfd_value.quantize(Q2),
        "margin": margin,
    }
    if record:
        record_snapshot(portfolio, valuation=result)
    return result


def refresh_portfolio_prices(portfolio: Portfolio):
    now = timezone.now()
    seen = set()
    for h in portfolio.holdings.select_related("instrument"):
        seen.add(h.instrument_id)
        tick(h.instrument, now)
    for pos in portfolio.positions.filter(status="OPEN").select_related("instrument"):
        if pos.instrument_id not in seen:
            seen.add(pos.instrument_id)
            tick(pos.instrument, now)


def record_snapshot(portfolio: Portfolio, valuation=None, force=False):
    last = portfolio.snapshots.order_by("-timestamp").first()
    if not force and last and (timezone.now() - last.timestamp).total_seconds() < SNAPSHOT_EVERY_SECONDS:
        return
    v = valuation or valuate_portfolio(portfolio, record=False)
    PortfolioSnapshot.objects.create(
        portfolio=portfolio, total_value=v["total_value"], cash=v["cash"],
        invested_value=v["invested_value"], net_contributions=v["net_contributions"],
    )


def allocation(valuation: dict) -> dict:
    by_type, by_sector, by_class = {}, {}, {}
    total = valuation["total_value"]
    labels = {"STOCK": "Acciones", "ETF": "ETFs"}
    class_labels = dict(Instrument.ASSET_CLASS_CHOICES)
    for h in valuation["holdings"]:
        by_type[labels[h["type"]]] = by_type.get(labels[h["type"]], ZERO) + h["market_value"]
        by_sector[h["sector"]] = by_sector.get(h["sector"], ZERO) + h["market_value"]
        cl = class_labels.get(h["asset_class"], h["asset_class"])
        by_class[cl] = by_class.get(cl, ZERO) + h["market_value"]
    for d in (by_type, by_sector, by_class):
        if valuation.get("cfd_value", ZERO) > 0:
            d["Posiciones CFD (margen)"] = valuation["cfd_value"]
        if valuation["cash"] > 0:
            d["Efectivo"] = valuation["cash"]

    def fmt(d):
        return sorted(
            [{"name": k, "value": v.quantize(Q2), "pct": float((v / total * 100).quantize(Q2)) if total else 0} for k, v in d.items()],
            key=lambda x: x["value"], reverse=True,
        )
    return {"by_type": fmt(by_type), "by_sector": fmt(by_sector), "by_asset_class": fmt(by_class)}


# ── Riesgo, diversificación y retroalimentación ──────────────────────────

def risk_metrics(portfolio: Portfolio, valuation: dict) -> dict:
    holdings = [h for h in valuation["holdings"] if h["market_value"] > 0]
    total = float(valuation["total_value"])
    invested = float(valuation["invested_value"])
    empty = {
        "volatility_annual": None, "expected_return_annual": None, "sharpe": None, "beta": None,
        "var95_1d": None, "max_drawdown_1y": None, "diversification_score": None,
        "effective_assets": None, "hhi": None,
    }
    if not holdings or total <= 0:
        return empty
    weights_inv = np.array([float(h["market_value"]) / invested for h in holdings])
    hhi = float((weights_inv ** 2).sum())
    effective = 1 / hhi if hhi else 0
    sectors = {h["sector"] for h in holdings}
    # 0–100: reparto entre activos (1 − HHI) ponderado por la variedad de sectores
    div_score = min(100.0, (1 - hhi) / 0.85 * 100) * min(1.0, len(sectors) / 4)

    insts = list(Instrument.objects.filter(symbol__in=[h["symbol"] for h in holdings]))
    order = {i.symbol: i for i in insts}
    insts = [order[h["symbol"]] for h in holdings]
    bench = Instrument.objects.filter(symbol=BENCHMARK_SYMBOL).first()
    with_bench = insts + ([bench] if bench and bench.symbol not in order else [])
    _, mat = aligned_returns(with_bench, 365)
    if len(mat) < 20:
        return {**empty, "diversification_score": round(div_score, 1), "effective_assets": round(effective, 2), "hhi": round(hhi, 4)}

    w_total = np.array([float(h["market_value"]) / total for h in holdings])  # el efectivo pondera con rendimiento 0
    asset_rets = mat[:, :len(insts)]
    port = asset_rets @ w_total
    rf = settings.SIMULATION["RISK_FREE_RATE"]
    vol = float(port.std(ddof=1) * math.sqrt(252))
    exp_ret = float((1 + port.mean()) ** 252 - 1)
    bench_rets = None
    if bench is not None:
        if bench.symbol in order:
            bench_rets = asset_rets[:, [i.symbol for i in insts].index(bench.symbol)]
        else:
            bench_rets = mat[:, -1]
    beta = None
    if bench_rets is not None:
        cov = np.cov(port, bench_rets)
        beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] else None
    curve = np.cumprod(1 + port)
    return {
        "volatility_annual": round(vol * 100, 2),
        "expected_return_annual": round(exp_ret * 100, 2),
        "sharpe": round((exp_ret - rf) / vol, 2) if vol else None,
        "beta": round(beta, 2) if beta is not None else None,
        "var95_1d": round(1.645 * float(port.std(ddof=1)) * total, 2),
        "max_drawdown_1y": round(max_drawdown(curve) * 100, 2),
        "diversification_score": round(div_score, 1),
        "effective_assets": round(effective, 2),
        "hhi": round(hhi, 4),
    }


def insights(portfolio: Portfolio, valuation: dict, risk: dict) -> list[dict]:
    """Retroalimentación educativa en lenguaje sencillo."""
    out = []
    total = valuation["total_value"]
    holdings = valuation["holdings"]
    risk_profile = portfolio.user.profile.risk_profile
    m = valuation.get("margin") or {}
    if m.get("margin_call"):
        out.append({"level": "warning", "title": f"Nivel de margen bajo: {m['margin_level']} %",
                    "text": f"Si baja de {m['stop_out_level']} % la plataforma cerrará tus posiciones con mayor pérdida. Aporta efectivo, reduce posiciones o ajusta tus stop loss."})
    if m.get("open_positions"):
        lev = list(portfolio.positions.filter(status="OPEN").values_list("leverage", "stop_loss"))
        if any(l >= 5 and sl is None for l, sl in lev):
            out.append({"level": "warning", "title": "Posiciones apalancadas sin stop loss",
                        "text": "Con apalancamiento alto, un movimiento pequeño en contra puede consumir todo el margen. Define un stop loss para limitar la pérdida máxima."})
    if not holdings and not m.get("open_positions"):
        out.append({"level": "info", "title": "Tu portafolio está en efectivo",
                    "text": "Aún no tienes inversiones. Ve a Mercado, elige un instrumento y haz tu primera compra."})
        return out
    if not holdings:
        return out or [{"level": "info", "title": "Solo operas con margen",
                        "text": "Este portafolio no tiene inversiones de contado; las métricas de diversificación aplican a la parte de contado."}]
    cash_pct = float(valuation["cash"] / total * 100) if total else 0
    if cash_pct > 50:
        out.append({"level": "warning", "title": f"{cash_pct:.0f} % de tu dinero está quieto",
                    "text": "El efectivo no genera rendimiento y la inflación le resta poder de compra. Considera invertir una parte o abrir una cuenta de ahorro."})
    top = holdings[0]
    if float(top["weight"]) > 40 and len(holdings) > 0:
        out.append({"level": "warning", "title": f"Alta concentración en {top['symbol']}",
                    "text": f"{top['symbol']} representa {top['weight']} % del portafolio. Si esa empresa cae, todo tu portafolio lo siente. Una regla común es no superar 20–25 % en un solo activo."})
    sectors = {h["sector"] for h in holdings}
    if len(holdings) >= 2 and len(sectors) == 1:
        out.append({"level": "warning", "title": "Todo está en un solo sector",
                    "text": f"Todas tus posiciones son de {next(iter(sectors))}. Los sectores suelen caer juntos; combinar sectores reduce el riesgo."})
    vol = risk.get("volatility_annual")
    if vol is not None:
        limits = {"conservador": 12, "moderado": 20, "agresivo": 35}
        if vol > limits.get(risk_profile, 20):
            out.append({"level": "warning", "title": "Más riesgo del que indica tu perfil",
                        "text": f"La volatilidad de tu portafolio es {vol} % anual y tu perfil es {risk_profile}. Agregar ETFs amplios o bonos (AGG, TLT) puede suavizar los movimientos."})
        elif vol < 8 and risk_profile == "agresivo":
            out.append({"level": "info", "title": "Portafolio muy conservador para tu perfil",
                        "text": "Con un perfil agresivo podrías asumir más renta variable a cambio de un mayor rendimiento esperado a largo plazo."})
    if risk.get("effective_assets") and risk["effective_assets"] >= 5 and len(sectors) >= 4:
        out.append({"level": "success", "title": "Buena diversificación",
                    "text": f"Tu portafolio se comporta como si tuvieras unos {risk['effective_assets']:.0f} activos de igual peso repartidos en {len(sectors)} sectores."})
    losers = [h for h in holdings if float(h["unrealized_pnl_pct"]) < -15]
    if losers:
        names = ", ".join(h["symbol"] for h in losers[:3])
        out.append({"level": "info", "title": "Posiciones con pérdidas fuertes",
                    "text": f"{names} pierden más de 15 %. Revisa si tu razón para invertir sigue vigente antes de decidir: vender por pánico materializa la pérdida."})
    if float(valuation["fees_paid"]) > float(valuation["net_contributions"] or 1) * 0.01:
        out.append({"level": "info", "title": "Las comisiones se acumulan",
                    "text": f"Has pagado {usd(valuation['fees_paid'])} en comisiones. Operar con mucha frecuencia reduce el rendimiento."})
    if not out:
        out.append({"level": "success", "title": "Todo en orden",
                    "text": "Tu portafolio no muestra señales de alerta. Revisa periódicamente y mantén tu estrategia."})
    return out


# ── Rendimiento histórico ────────────────────────────────────────────────

def snapshot_series(portfolio: Portfolio, limit=500):
    snaps = list(portfolio.snapshots.order_by("-timestamp")[:limit])
    snaps.reverse()
    return [{
        "t": s.timestamp.isoformat(),
        "value": float(s.total_value),
        "contributions": float(s.net_contributions),
        "invested": float(s.invested_value),
    } for s in snaps]


def backtest(portfolio: Portfolio, days=365) -> dict:
    """¿Cómo le habría ido a la composición ACTUAL del portafolio en el último periodo?"""
    holdings = list(portfolio.holdings.select_related("instrument"))
    if not holdings:
        return {"points": [], "portfolio_return": None, "benchmark_return": None}
    since = timezone.localdate() - timedelta(days=days)
    syms = [h.instrument_id for h in holdings]
    bench = Instrument.objects.filter(symbol=BENCHMARK_SYMBOL).first()
    ids = syms + ([bench.id] if bench else [])
    bars = PriceBar.objects.filter(instrument_id__in=ids, date__gte=since).values_list("instrument_id", "date", "close")
    table = {}
    for iid, d, c in bars:
        table.setdefault(d, {})[iid] = float(c)
    dates = sorted(d for d, row in table.items() if all(i in row for i in ids))
    if len(dates) < 2:
        return {"points": [], "portfolio_return": None, "benchmark_return": None}
    cash = float(portfolio.cash)
    values = [cash + sum(float(h.quantity) * table[d][h.instrument_id] for h in holdings) for d in dates]
    start_value = values[0]
    points = []
    for d, v in zip(dates, values):
        p = {"date": d.isoformat(), "portfolio": round(v, 2)}
        if bench:
            p["benchmark"] = round(start_value * table[d][bench.id] / table[dates[0]][bench.id], 2)
        points.append(p)
    return {
        "points": points,
        "portfolio_return": round((values[-1] / start_value - 1) * 100, 2),
        "benchmark_return": round((points[-1]["benchmark"] / start_value - 1) * 100, 2) if bench else None,
        "benchmark_symbol": BENCHMARK_SYMBOL,
    }
