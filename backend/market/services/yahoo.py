"""
Sincronización OPCIONAL con datos reales de Yahoo Finance.

    python manage.py sync_market --real

Si Yahoo no responde (sin internet, bloqueo, cambio de API) el instrumento conserva
sus datos simulados. El resto del sistema funciona igual en ambos casos.
"""
import logging
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

import requests
from django.db import transaction
from django.utils import timezone

from market.models import Instrument, PriceBar

log = logging.getLogger(__name__)
HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
HEADERS = {"User-Agent": "Mozilla/5.0 (AuraFarmers simulador educativo)"}


def fetch_daily(symbol: str, range_: str = "2y"):
    for host in HOSTS:
        url = f"https://{host}/v8/finance/chart/{symbol}"
        try:
            r = requests.get(url, params={"interval": "1d", "range": range_}, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            res = r.json()["chart"]["result"][0]
            ts = res["timestamp"]
            q = res["indicators"]["quote"][0]
            rows = []
            for i, t in enumerate(ts):
                vals = [q["open"][i], q["high"][i], q["low"][i], q["close"][i]]
                if any(v is None for v in vals):
                    continue
                rows.append((datetime.fromtimestamp(t, dt_tz.utc).date(), *vals, q["volume"][i] or 0))
            if rows:
                return rows
        except Exception as exc:  # noqa: BLE001
            log.warning("Yahoo %s falló para %s: %s", host, symbol, exc)
    return None


@transaction.atomic
def sync_instrument(inst: Instrument) -> bool:
    rows = fetch_daily(inst.symbol)
    if not rows or len(rows) < 60:
        return False
    PriceBar.objects.filter(instrument=inst).delete()
    q = lambda v: Decimal(str(round(v, 4)))  # noqa: E731
    PriceBar.objects.bulk_create([
        PriceBar(instrument=inst, date=d, open=q(o), high=q(h), low=q(l), close=q(c), volume=int(v))
        for d, o, h, l, c, v in rows
    ], ignore_conflicts=True)
    today = timezone.localdate()
    PriceBar.objects.filter(instrument=inst, date__gte=today).delete()
    last = inst.bars.order_by("-date").first()
    inst.anchor_price = last.close
    inst.previous_close = last.close
    inst.current_price = last.close
    inst.last_tick_at = timezone.now()
    inst.history_synced_on = today
    inst.data_source = "yahoo"
    inst.save()
    return True
