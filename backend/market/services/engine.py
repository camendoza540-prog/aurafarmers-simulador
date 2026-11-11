"""
Motor de precios del simulador.

Modelo: movimiento browniano geométrico (GBM) con un factor de mercado común,
de modo que los activos se muevan de forma correlacionada (como en la realidad):

    r_i = (μ_i − σ_i²/2)·dt + β_i·σ_m·√dt·Z_m + σ_idio_i·√dt·Z_i  (+ saltos ocasionales)

Los números aleatorios se derivan de semillas deterministas (símbolo + fecha), así la
historia generada es reproducible y todas las acciones comparten el mismo shock de mercado.
"""
import hashlib
import logging
import math
import random
import sys
import threading
import time
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from market.models import Instrument, IntradayBar, PriceBar

log = logging.getLogger(__name__)
TRADING_DAYS = 252
TRADING_HOURS_PER_YEAR = TRADING_DAYS * 6.5
Q4 = Decimal("0.0001")


def _cfg(key):
    return settings.SIMULATION[key]


def _seed(*parts) -> int:
    raw = "|".join(str(p) for p in parts).encode()
    return int(hashlib.sha256(raw).hexdigest()[:16], 16)


def _gauss(*parts) -> float:
    return random.Random(_seed(*parts)).gauss(0.0, 1.0)


def _uniform(*parts) -> float:
    return random.Random(_seed(*parts)).random()


def _d(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Q4, rounding=ROUND_HALF_UP)


def business_days(start: date, end: date):
    """Días hábiles (lunes a viernes) entre start y end, inclusive."""
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def last_business_day_before(day: date) -> date:
    d = day - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _idio_sigma(inst: Instrument) -> float:
    sm = _cfg("MARKET_VOLATILITY")
    var = inst.annual_volatility ** 2 - (inst.beta ** 2) * sm ** 2
    return math.sqrt(max(var, (0.25 * inst.annual_volatility) ** 2))


def daily_log_return(inst: Instrument, day: date) -> float:
    """Rendimiento logarítmico de un día hábil (determinista por símbolo y fecha)."""
    dt = 1 / TRADING_DAYS
    sm = _cfg("MARKET_VOLATILITY")
    sigma = inst.annual_volatility
    zm = _gauss("market", day.isoformat())
    zi = _gauss(inst.symbol, day.isoformat())
    r = (inst.annual_drift - 0.5 * sigma ** 2) * dt
    r += inst.beta * sm * math.sqrt(dt) * zm + _idio_sigma(inst) * math.sqrt(dt) * zi
    # Saltos: noticias inesperadas (≈1,5 % de los días)
    if _uniform(inst.symbol, "jump", day.isoformat()) < 0.015:
        r += _gauss(inst.symbol, "jumpsize", day.isoformat()) * sigma * math.sqrt(dt) * 3 - 0.004
    return r


def _bar_from(inst: Instrument, day: date, prev_close: float, close: float) -> PriceBar:
    sd = inst.annual_volatility / math.sqrt(TRADING_DAYS)
    gap = _gauss(inst.symbol, "gap", day.isoformat()) * sd * 0.25
    open_ = prev_close * math.exp(gap)
    hi_noise = abs(_gauss(inst.symbol, "hi", day.isoformat())) * sd * 0.45
    lo_noise = abs(_gauss(inst.symbol, "lo", day.isoformat())) * sd * 0.45
    high = max(open_, close) * (1 + hi_noise)
    low = min(open_, close) * (1 - lo_noise)
    vol_factor = math.exp(0.35 * _gauss(inst.symbol, "vol", day.isoformat()))
    return PriceBar(
        instrument=inst, date=day, open=_d(open_), high=_d(high), low=_d(low),
        close=_d(close), volume=int(inst.base_volume * vol_factor),
    )


@transaction.atomic
def generate_history(inst: Instrument, years: int | None = None) -> int:
    """Genera la historia diaria del instrumento terminando en su precio de referencia."""
    years = years or _cfg("HISTORY_YEARS")
    today = timezone.localdate()
    end = last_business_day_before(today)
    start = end - timedelta(days=int(365 * years))
    days = list(business_days(start, end))

    log_returns = [daily_log_return(inst, d) for d in days]
    # Camino logarítmico relativo y escalado para que el último cierre = precio de referencia
    path, acc = [], 0.0
    for r in log_returns:
        acc += r
        path.append(acc)
    scale = float(inst.anchor_price) / math.exp(path[-1])
    closes = [scale * math.exp(p) for p in path]

    PriceBar.objects.filter(instrument=inst).delete()
    IntradayBar.objects.filter(instrument=inst).delete()
    cache.delete(f"intraday:{inst.symbol}")
    bars = []
    prev = closes[0] / math.exp(log_returns[0])
    for d, c in zip(days, closes):
        bars.append(_bar_from(inst, d, prev, c))
        prev = c
    PriceBar.objects.bulk_create(bars, batch_size=1000)

    inst.previous_close = bars[-1].close
    inst.current_price = bars[-1].close
    inst.last_tick_at = timezone.now()
    inst.history_synced_on = today
    inst.data_source = "simulado"
    inst.save()
    return len(bars)


def ensure_up_to_date(inst: Instrument) -> bool:
    """Completa los días hábiles faltantes (si el servidor estuvo apagado) una vez por día.
    Devuelve True si tuvo que generar días nuevos."""
    today = timezone.localdate()
    if inst.history_synced_on == today:
        return False
    last = inst.bars.filter(date__lt=today).order_by("-date").first()
    if last is None:
        generate_history(inst)
        return True
    missing = list(business_days(last.date + timedelta(days=1), last_business_day_before(today)))
    prev = float(last.close)
    new_bars = []
    for d in missing:
        close = prev * math.exp(daily_log_return(inst, d))
        new_bars.append(_bar_from(inst, d, prev, close))
        prev = close
    if new_bars:
        PriceBar.objects.bulk_create(new_bars, ignore_conflicts=True)
        inst.current_price = new_bars[-1].close
        inst.last_tick_at = timezone.now()
    inst.previous_close = _d(prev)
    if not inst.current_price:
        inst.current_price = inst.previous_close
    inst.history_synced_on = today
    inst.save(update_fields=["previous_close", "current_price", "last_tick_at", "history_synced_on"])
    return bool(new_bars)


# ── Intradía: velas de 1 minuto ───────────────────────────────────────────

def _minute_sigma(inst: Instrument) -> float:
    """Volatilidad de un minuto real (que equivale a MARKET_SPEED minutos de mercado)."""
    market_minutes = _cfg("MARKET_SPEED")
    return inst.annual_volatility * math.sqrt(market_minutes / (TRADING_HOURS_PER_YEAR * 60))


def _minute_floor(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def _walk(inst: Instrument, n: int, start: float | None, end: float | None, seed_key) -> list[tuple]:
    """Camino de n minutos (OHLC). Si `end` se da, termina exactamente ahí (puente browniano)."""
    import numpy as np

    rng = np.random.default_rng(_seed(inst.symbol, "intraday", seed_key))
    sig = _minute_sigma(inst)
    steps = rng.standard_normal(n) * sig - 0.5 * sig * sig
    path = np.cumsum(steps)
    if end is not None and start is not None:
        # Puente: corrige linealmente para llegar de start a end
        target = math.log(end / start)
        path = path + (target - path[-1]) * np.arange(1, n + 1) / n
        closes = start * np.exp(path)
    elif end is not None:
        closes = end * np.exp(path - path[-1])
    else:
        closes = start * np.exp(path)
    opens = np.concatenate([[closes[0] * math.exp(-steps[0])], closes[:-1]])
    wick = np.abs(rng.standard_normal((n, 2))) * sig * 0.6
    highs = np.maximum(opens, closes) * (1 + wick[:, 0])
    lows = np.minimum(opens, closes) * (1 - wick[:, 1])
    vols = (inst.base_volume / 390) * np.exp(0.4 * rng.standard_normal(n))
    return list(zip(opens, highs, lows, closes, vols))


def _save_minutes(inst: Instrument, first_ts: datetime, rows: list[tuple]):
    IntradayBar.objects.bulk_create([
        IntradayBar(instrument=inst, ts=first_ts + timedelta(minutes=i), open=_d(o), high=_d(h),
                    low=_d(l), close=_d(c), volume=int(v))
        for i, (o, h, l, c, v) in enumerate(rows)
    ], batch_size=2000, ignore_conflicts=True)


def ensure_intraday(inst: Instrument, now: datetime | None = None, daily_jump: bool = False):
    """Garantiza velas de 1 minuto continuas hasta el minuto actual (relleno y poda)."""
    now = now or timezone.now()
    key = f"intraday:{inst.symbol}"
    current_min = _minute_floor(now)
    if not daily_jump and cache.get(key) == current_min:
        return
    max_minutes = _cfg("INTRADAY_DAYS") * 1440
    last = inst.intraday.order_by("-ts").first()
    price = float(inst.current_price or inst.previous_close or inst.anchor_price)

    if last is None:
        # Primera vez: historia intradía que termina en el precio actual
        first = current_min - timedelta(minutes=max_minutes)
        rows = _walk(inst, max_minutes, None, price, first.isoformat())
        _save_minutes(inst, first, rows)
    else:
        gap = int((current_min - last.ts).total_seconds() // 60) - 1
        if gap > 0:
            gap = min(gap, max_minutes)
            first = current_min - timedelta(minutes=gap)
            start = float(last.close)
            # Si el motor diario saltó días, el camino debe llegar al nuevo precio
            rows = _walk(inst, gap, start, price if daily_jump else None, first.isoformat())
            _save_minutes(inst, first, rows)
            if not daily_jump:
                inst.current_price = _d(rows[-1][3])
            inst.last_tick_at = now
            inst.save(update_fields=["current_price", "last_tick_at"])
        # Poda de velas viejas (como mucho una vez por hora)
        if cache.get(f"{key}:pruned") is None:
            IntradayBar.objects.filter(instrument=inst, ts__lt=current_min - timedelta(minutes=max_minutes + 720)).delete()
            cache.set(f"{key}:pruned", True, 3600)
    cache.set(key, current_min, 120)


def tick(inst: Instrument, now: datetime | None = None, check_orders: bool = True) -> bool:
    """Avanza el precio en vivo según los segundos transcurridos y actualiza las velas."""
    if clock_running() and threading.current_thread().name != "reloj-de-mercado":
        return False  # el reloj en segundo plano es el único que escribe precios
    now = now or timezone.now()
    jumped = ensure_up_to_date(inst)
    ensure_intraday(inst, now, daily_jump=jumped)
    if inst.last_tick_at is None:
        inst.last_tick_at = now
        inst.save(update_fields=["last_tick_at"])
        return False
    elapsed = (now - inst.last_tick_at).total_seconds()
    min_s = _cfg("TICK_MIN_SECONDS")
    if elapsed < min_s:
        return False
    # Candado no bloqueante: si otra petición ya está moviendo este precio, se usa el último
    # precio guardado en lugar de escribir dos veces (SQLite admite un solo escritor).
    if not cache.add(f"tick-lock:{inst.symbol}", 1, timeout=max(int(min_s), 1)):
        return False

    elapsed = min(elapsed, 120)  # los huecos mayores ya los cubrió ensure_intraday
    dt = elapsed * _cfg("MARKET_SPEED") / 3600 / TRADING_HOURS_PER_YEAR
    sm = _cfg("MARKET_VOLATILITY")
    bucket = int(now.timestamp() // min_s)
    zm = _gauss("market-tick", bucket)
    zi = _gauss(inst.symbol, "tick", bucket)
    sigma = inst.annual_volatility
    r = (inst.annual_drift - 0.5 * sigma ** 2) * dt + inst.beta * sm * math.sqrt(dt) * zm + _idio_sigma(inst) * math.sqrt(dt) * zi
    old_price = inst.current_price or inst.previous_close
    new_price = _d(float(old_price) * math.exp(r))
    vol_add = int(inst.base_volume / 390 * (elapsed / 60) * math.exp(0.3 * zi))

    # Vela de 1 minuto
    minute = _minute_floor(now)
    bar, created = IntradayBar.objects.get_or_create(
        instrument=inst, ts=minute,
        defaults=dict(open=old_price, high=max(old_price, new_price), low=min(old_price, new_price),
                      close=new_price, volume=vol_add),
    )
    if not created:
        bar.high = max(bar.high, new_price)
        bar.low = min(bar.low, new_price)
        bar.close = new_price
        bar.volume += vol_add
        bar.save(update_fields=["high", "low", "close", "volume"])

    # Vela diaria
    today = timezone.localdate()
    day, created = PriceBar.objects.get_or_create(
        instrument=inst, date=today,
        defaults=dict(open=old_price, high=max(old_price, new_price), low=min(old_price, new_price),
                      close=new_price, volume=vol_add),
    )
    if not created:
        day.high = max(day.high, new_price)
        day.low = min(day.low, new_price)
        day.close = new_price
        day.volume += vol_add
        day.save(update_fields=["high", "low", "close", "volume"])

    inst.current_price = new_price
    inst.last_tick_at = now
    inst.save(update_fields=["current_price", "last_tick_at"])

    if check_orders:
        # Take profit, stop loss y cierre forzoso por margen
        from portfolios.trading import check_triggers
        check_triggers(inst)
    return True


# ── Reloj de mercado en segundo plano ─────────────────────────────────────
# Un único hilo mueve todos los precios y ejecuta TP/SL/cierres forzosos. Así las
# consultas de los usuarios solo leen, y las órdenes se ejecutan aunque nadie mire.
_clock = {"thread": None}
_clock_lock = threading.Lock()


def clock_running() -> bool:
    t = _clock["thread"]
    return t is not None and t.is_alive()


def start_market_clock() -> bool:
    if not settings.SIMULATION.get("MARKET_CLOCK", True) or "test" in sys.argv:
        return False
    with _clock_lock:
        if not clock_running():
            t = threading.Thread(target=_clock_loop, name="reloj-de-mercado", daemon=True)
            t.start()
            _clock["thread"] = t
            log.info("Reloj de mercado iniciado")
    return True


def _clock_loop():
    from django.db import close_old_connections

    interval = max(float(_cfg("TICK_MIN_SECONDS")), 1.0)
    while True:
        started = time.monotonic()
        try:
            now = timezone.now()
            # Una sola transacción por ciclo: un único bloqueo de escritura en lugar de ~200
            with transaction.atomic():
                for inst in Instrument.objects.filter(is_active=True):
                    tick(inst, now)
        except Exception:  # noqa: BLE001 — el reloj nunca debe detenerse
            log.exception("Error en el reloj de mercado")
        finally:
            close_old_connections()
        time.sleep(max(0.2, interval - (time.monotonic() - started)))


def refresh_all(force: bool = False):
    """Actualiza todos los instrumentos activos (con limitador global para no saturar)."""
    if not force and start_market_clock():
        return  # el reloj en segundo plano ya los mantiene al día
    now = timezone.now()
    # Solo una petición a la vez refresca todo el catálogo (cache.add es atómico)
    if not force and not cache.add("market:refresh-all", 1, timeout=max(int(_cfg("TICK_MIN_SECONDS")) * 2, 2)):
        return
    for inst in Instrument.objects.filter(is_active=True):
        tick(inst, now)


def refresh_symbols(symbols):
    if start_market_clock():
        return
    now = timezone.now()
    for inst in Instrument.objects.filter(symbol__in=list(symbols), is_active=True):
        tick(inst, now)


def refresh_open_positions():
    """Actualiza los instrumentos con órdenes vivas (posiciones CFD o protecciones TP/SL)."""
    from portfolios.models import Holding, Position

    if start_market_clock():
        return
    syms = set(Position.objects.filter(status="OPEN").values_list("instrument__symbol", flat=True))
    syms |= set(Holding.objects.exclude(take_profit=None, stop_loss=None).values_list("instrument__symbol", flat=True))
    if syms:
        refresh_symbols(syms)
