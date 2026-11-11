"""
Trading con margen (CFD) y órdenes de protección.

Reglas (inspiradas en brókeres minoristas regulados por ESMA, como XTB):
  · Apalancamiento máximo ESMA: divisas mayores 1:30, exóticas e índices 1:20,
    oro 1:20, otras materias primas 1:10, acciones/ETF 1:5, criptomonedas 1:2.
  · En pares como USDJPY el precio está en yenes: ganancias y márgenes se convierten a USD.
  · Margen = nocional / apalancamiento; se bloquea del efectivo del portafolio.
  · Largos abren al ask y cierran al bid; cortos abren al bid y cierran al ask (spread).
  · Take profit: orden límite, se ejecuta al precio fijado.
  · Stop loss: orden stop, se ejecuta al precio fijado o peor si el precio saltó (gap).
  · Nivel de margen = capital / margen usado. < 100 %: aviso. < 50 %: cierre forzoso.
  · Protección de saldo negativo: una posición nunca devuelve menos de 0.
"""
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from config.formatting import usd
from market.models import Instrument

from .models import Holding, Portfolio, Position, Transaction

Q2, Q4, Q6 = Decimal("0.01"), Decimal("0.0001"), Decimal("0.000001")
LEVERAGE_OPTIONS = [1, 2, 3, 5, 10, 20, 30]
GAP_TOLERANCE = Decimal("0.005")


class TradingError(Exception):
    pass


def _dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        raise TradingError("Precio inválido.")


def validate_protection(side: str, ref_price: Decimal, take_profit, stop_loss):
    tp, sl = _dec(take_profit), _dec(stop_loss)
    for name, v in (("take profit", tp), ("stop loss", sl)):
        if v is not None and v <= 0:
            raise TradingError(f"El {name} debe ser mayor que cero.")
    if side == "LONG":
        if tp is not None and tp <= ref_price:
            raise TradingError(f"En una compra el take profit debe estar por encima del precio actual ({usd(ref_price, 4)}).")
        if sl is not None and sl >= ref_price:
            raise TradingError(f"En una compra el stop loss debe estar por debajo del precio actual ({usd(ref_price, 4)}).")
    else:
        if tp is not None and tp >= ref_price:
            raise TradingError(f"En una venta en corto el take profit debe estar por debajo del precio actual ({usd(ref_price, 4)}).")
        if sl is not None and sl <= ref_price:
            raise TradingError(f"En una venta en corto el stop loss debe estar por encima del precio actual ({usd(ref_price, 4)}).")
    return tp, sl


def margin_status(portfolio: Portfolio) -> dict:
    """Estado de la cuenta de margen del portafolio (solo posiciones CFD)."""
    positions = list(portfolio.positions.filter(status="OPEN").select_related("instrument"))
    used = sum((p.margin for p in positions), Decimal("0"))
    upnl = sum((p.unrealized_pnl() for p in positions), Decimal("0"))
    equity = portfolio.cash + used + upnl
    level = (equity / used * 100).quantize(Q2) if used > 0 else None
    cfg = settings.SIMULATION
    return {
        "open_positions": len(positions),
        "margin_used": used.quantize(Q2),
        "unrealized_pnl": upnl.quantize(Q2),
        "equity": equity.quantize(Q2),
        "free_margin": max(equity - used, Decimal("0")).quantize(Q2),
        "margin_level": level,
        "margin_call_level": cfg["MARGIN_CALL_LEVEL"],
        "stop_out_level": cfg["STOP_OUT_LEVEL"],
        "margin_call": level is not None and level < cfg["MARGIN_CALL_LEVEL"],
    }


@transaction.atomic
def open_position(portfolio: Portfolio, symbol: str, side: str, leverage: int = 1,
                  quantity=None, margin_amount=None, take_profit=None, stop_loss=None) -> Position:
    from market.services.engine import tick

    side = (side or "").upper()
    if side not in ("LONG", "SHORT"):
        raise TradingError("Dirección inválida: usa LONG (compra) o SHORT (venta).")
    try:
        inst = Instrument.objects.get(symbol=(symbol or "").upper(), is_active=True)
    except Instrument.DoesNotExist:
        raise TradingError("Instrumento no encontrado.")
    try:
        leverage = int(leverage)
    except (TypeError, ValueError):
        raise TradingError("Apalancamiento inválido.")
    if leverage not in LEVERAGE_OPTIONS:
        raise TradingError(f"Apalancamientos permitidos: {', '.join(f'1:{x}' for x in LEVERAGE_OPTIONS)}.")
    if leverage > inst.max_leverage:
        raise TradingError(f"El apalancamiento máximo para {inst.symbol} es 1:{inst.max_leverage} (límite ESMA para su clase de activo).")

    tick(inst, check_orders=False)
    inst.refresh_from_db()
    price = inst.ask if side == "LONG" else inst.bid
    fx = inst.usd_factor(price)  # 1 para pares en USD; 1/precio en USDJPY, USDCOP…
    if margin_amount not in (None, ""):
        margin_amount = _dec(margin_amount)
        if margin_amount <= 0:
            raise TradingError("El margen debe ser mayor que cero.")
        quantity = (margin_amount * leverage / (price * fx)).quantize(Q6, ROUND_DOWN)
    quantity = _dec(quantity)
    if quantity is None or quantity <= 0:
        raise TradingError("Indica unidades o un margen en USD.")
    quantity = quantity.quantize(Q6, ROUND_DOWN)
    notional = (quantity * price * fx).quantize(Q2, ROUND_HALF_UP)
    margin = (notional / leverage).quantize(Q2, ROUND_HALF_UP)
    if margin < Decimal("1"):
        raise TradingError("La operación es demasiado pequeña (margen mínimo US$ 1).")
    tp, sl = validate_protection(side, inst.current_price, take_profit, stop_loss)

    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
    status = margin_status(portfolio)
    available = min(portfolio.cash, status["free_margin"]) if status["margin_used"] > 0 else portfolio.cash
    if margin > available:
        raise TradingError(
            f"Margen insuficiente: la operación requiere {usd(margin)} y tienes {usd(available)} disponibles en el portafolio."
        )
    portfolio.cash -= margin
    portfolio.save(update_fields=["cash", "updated_at"])
    pos = Position.objects.create(
        portfolio=portfolio, instrument=inst, side=side, quantity=quantity, leverage=leverage,
        entry_price=price, notional=notional, margin=margin, take_profit=tp, stop_loss=sl,
    )
    Transaction.objects.create(
        portfolio=portfolio, instrument=inst, type="CFD_OPEN", quantity=quantity, price=price,
        fee=Decimal("0"), total=margin, cash_after=portfolio.cash, position=pos,
        note=f"{'Compra' if side == 'LONG' else 'Venta en corto'} 1:{leverage}",
    )
    from .services import record_snapshot
    record_snapshot(portfolio, force=True)
    return pos


@transaction.atomic
def close_position(pos: Position, reason: str = "MANUAL", price=None) -> Position:
    pos = Position.objects.select_for_update().select_related("instrument", "portfolio").get(pk=pos.pk)
    if pos.status != "OPEN":
        raise TradingError("La posición ya está cerrada.")
    exit_price = _dec(price) if price is not None else pos.exit_price()
    pnl = ((exit_price - pos.entry_price) * pos.quantity * pos.direction
           * pos.instrument.usd_factor(exit_price)).quantize(Q2, ROUND_HALF_UP)
    credit = pos.margin + pnl
    if credit < 0:  # protección de saldo negativo
        credit = Decimal("0.00")
    realized = credit - pos.margin
    portfolio = Portfolio.objects.select_for_update().get(pk=pos.portfolio_id)
    portfolio.cash += credit
    portfolio.save(update_fields=["cash", "updated_at"])
    pos.status = "CLOSED"
    pos.closed_at = timezone.now()
    pos.close_price = exit_price
    pos.close_reason = reason
    pos.realized_pnl = realized
    pos.save()
    Transaction.objects.create(
        portfolio=portfolio, instrument=pos.instrument, type="CFD_CLOSE", quantity=pos.quantity,
        price=exit_price, fee=Decimal("0"), total=credit, realized_pnl=realized, cash_after=portfolio.cash,
        position=pos, note=pos.get_close_reason_display(),
    )
    from .services import record_snapshot
    record_snapshot(portfolio, force=True)
    return pos


def update_protection(pos: Position, take_profit=None, stop_loss=None) -> Position:
    if pos.status != "OPEN":
        raise TradingError("Solo puedes modificar posiciones abiertas.")
    tp, sl = validate_protection(pos.side, pos.instrument.current_price, take_profit, stop_loss)
    pos.take_profit, pos.stop_loss = tp, sl
    pos.save(update_fields=["take_profit", "stop_loss"])
    return pos


def set_holding_protection(holding: Holding, take_profit=None, stop_loss=None) -> Holding:
    tp, sl = validate_protection("LONG", holding.instrument.current_price, take_profit, stop_loss)
    holding.take_profit, holding.stop_loss = tp, sl
    holding.save(update_fields=["take_profit", "stop_loss"])
    return holding


def _stop_fill(trigger: Decimal, market: Decimal, adverse_if_lower: bool) -> Decimal:
    """Precio de ejecución de un stop: el nivel fijado, o el de mercado si hubo salto."""
    if abs(market - trigger) / trigger <= GAP_TOLERANCE:
        return trigger
    return min(trigger, market) if adverse_if_lower else max(trigger, market)


def check_triggers(inst: Instrument):
    """Ejecuta take profit, stop loss y cierres forzosos tras un movimiento de precio."""
    from .services import TradeError, execute_trade

    bid, ask = inst.bid, inst.ask
    touched = set()

    def _safe_close(pos, reason, price):
        # Otra petición pudo cerrarla un instante antes (dos usuarios viendo el mismo activo)
        try:
            close_position(pos, reason, price)
        except TradingError:
            pass

    for pos in Position.objects.filter(instrument=inst, status="OPEN").select_related("instrument"):
        pos.instrument = inst
        touched.add(pos.portfolio_id)
        if pos.side == "LONG":
            if pos.take_profit and bid >= pos.take_profit:
                _safe_close(pos, "TP", pos.take_profit)
            elif pos.stop_loss and bid <= pos.stop_loss:
                _safe_close(pos, "SL", _stop_fill(pos.stop_loss, bid, adverse_if_lower=True))
        else:
            if pos.take_profit and ask <= pos.take_profit:
                _safe_close(pos, "TP", pos.take_profit)
            elif pos.stop_loss and ask >= pos.stop_loss:
                _safe_close(pos, "SL", _stop_fill(pos.stop_loss, ask, adverse_if_lower=False))

    price = inst.current_price
    for h in Holding.objects.filter(instrument=inst).exclude(take_profit=None, stop_loss=None).select_related("portfolio"):
        hit = None
        if h.take_profit and price >= h.take_profit:
            hit = "Take profit"
        elif h.stop_loss and price <= h.stop_loss:
            hit = "Stop loss"
        if hit:
            try:
                execute_trade(h.portfolio, inst.symbol, "SELL", quantity=h.quantity, note=hit)
            except TradeError:
                pass

    stop_out = Decimal(settings.SIMULATION["STOP_OUT_LEVEL"])
    for pid in touched:
        portfolio = Portfolio.objects.get(pk=pid)
        for _ in range(20):
            st = margin_status(portfolio)
            if st["margin_level"] is None or st["margin_level"] >= stop_out:
                break
            open_now = list(portfolio.positions.filter(status="OPEN").select_related("instrument"))
            if not open_now:
                break
            _safe_close(min(open_now, key=lambda p: p.unrealized_pnl()), "STOP_OUT", None)
            portfolio.refresh_from_db()


def position_payload(pos: Position) -> dict:
    inst = pos.instrument
    out = {
        "id": pos.id, "portfolio": pos.portfolio_id, "portfolio_name": pos.portfolio.name,
        "symbol": inst.symbol, "name": inst.name, "type": inst.type, "quote_currency": inst.quote_currency,
        "side": pos.side, "side_label": pos.get_side_display(),
        "quantity": pos.quantity, "leverage": pos.leverage, "entry_price": pos.entry_price,
        "notional": pos.notional, "margin": pos.margin,
        "take_profit": pos.take_profit, "stop_loss": pos.stop_loss,
        "status": pos.status, "opened_at": pos.opened_at, "closed_at": pos.closed_at,
        "close_price": pos.close_price, "close_reason": pos.close_reason,
        "close_reason_label": pos.get_close_reason_display() if pos.close_reason else "",
        "realized_pnl": pos.realized_pnl,
    }
    if pos.status == "OPEN":
        pnl = pos.unrealized_pnl()
        out.update({
            "current_price": pos.exit_price(),
            "unrealized_pnl": pnl,
            "pnl_pct_margin": float((pnl / pos.margin * 100).quantize(Q2)) if pos.margin else 0.0,
            "liquidation_hint": float(pos.entry_price * (1 - pos.direction * Decimal("0.5") / pos.leverage)),
        })
    return out
