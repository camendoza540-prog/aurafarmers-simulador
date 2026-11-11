"""
Velas OHLCV por temporalidad para el gráfico interactivo.

Intradía (1m, 5m, 15m, 30m, 1h): a partir de velas de 1 minuto en reloj real.
Diario, semanal y mensual (1D, 1S, 1M): a partir de la historia diaria.

Los tiempos se devuelven en segundos UNIX desplazados a la hora local de Bogotá,
porque la librería de gráficos los muestra tal cual (sin zona horaria).
"""
from datetime import datetime, time, timedelta, timezone as dt_tz

from django.utils import timezone

from market.models import Instrument

INTRADAY = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60}
DAILY = {"1D", "1S", "1M"}
TIMEFRAMES = list(INTRADAY) + ["1D", "1S", "1M"]


def _local_epoch(dt: datetime) -> int:
    local = timezone.localtime(dt)
    return int(local.replace(tzinfo=dt_tz.utc).timestamp())


def _date_epoch(d) -> int:
    return int(datetime.combine(d, time(0, 0), tzinfo=dt_tz.utc).timestamp())


def _merge(group):
    return {
        "open": group[0]["open"], "high": max(g["high"] for g in group),
        "low": min(g["low"] for g in group), "close": group[-1]["close"],
        "volume": sum(g["volume"] for g in group),
    }


def candles(inst: Instrument, tf: str = "5m", limit: int = 600) -> list[dict]:
    tf = tf if tf in TIMEFRAMES else "5m"
    out = []
    if tf in INTRADAY:
        step = INTRADAY[tf]
        since = timezone.now() - timedelta(minutes=step * (limit + 1))
        rows = inst.intraday.filter(ts__gte=since).order_by("ts").values("ts", "open", "high", "low", "close", "volume")
        buckets = {}
        for r in rows:
            t = _local_epoch(r["ts"])
            key = t - (t % (step * 60))
            buckets.setdefault(key, []).append({k: float(r[k]) if k != "volume" else r[k] for k in ("open", "high", "low", "close", "volume")})
        for key in sorted(buckets):
            out.append({"time": key, **_merge(buckets[key])})
    else:
        rows = list(inst.bars.order_by("date").values("date", "open", "high", "low", "close", "volume"))
        conv = [{"date": r["date"], **{k: float(r[k]) for k in ("open", "high", "low", "close")}, "volume": r["volume"]} for r in rows]
        if tf == "1D":
            out = [{"time": _date_epoch(r["date"]), **{k: r[k] for k in ("open", "high", "low", "close", "volume")}} for r in conv]
        else:
            buckets = {}
            for r in conv:
                d = r["date"]
                start = d - timedelta(days=d.weekday()) if tf == "1S" else d.replace(day=1)
                buckets.setdefault(start, []).append(r)
            out = [{"time": _date_epoch(k), **_merge(v)} for k, v in sorted(buckets.items())]
    for c in out:
        for k in ("open", "high", "low", "close"):
            c[k] = round(c[k], 4)
    return out[-limit:]
