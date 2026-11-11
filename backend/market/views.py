from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .catalog import BENCHMARK_SYMBOL
from .models import Instrument
from .serializers import InstrumentDetailSerializer, InstrumentListSerializer, InstrumentSerializer
from .services.candles import TIMEFRAMES, candles
from .services.engine import refresh_all, refresh_symbols, tick
from .services.news import get_news
from .services.stats import RANGES, history_payload, instrument_stats

# Indicadores que emiten un juicio de dirección: el usuario decide con el gráfico y las noticias
OPINION_KEYS = ("trend", "trend_text", "rsi_text")


@api_view(["GET"])
def instrument_list(request):
    refresh_all()
    qs = Instrument.objects.filter(is_active=True)
    t = request.query_params.get("type")
    if t in ("STOCK", "ETF"):
        qs = qs.filter(type=t)
    sector = request.query_params.get("sector")
    if sector:
        qs = qs.filter(sector=sector)
    q = request.query_params.get("search")
    if q:
        qs = qs.filter(Q(symbol__icontains=q) | Q(name__icontains=q) | Q(sector__icontains=q))
    return Response(InstrumentListSerializer(qs, many=True).data)


@api_view(["GET"])
def quotes(request):
    """Cotizaciones livianas (para refrescar precios cada pocos segundos)."""
    symbols = request.query_params.get("symbols")
    qs = Instrument.objects.filter(is_active=True)
    if symbols:
        wanted = [s.strip().upper() for s in symbols.split(",") if s.strip()][:30]
        refresh_symbols(wanted)
        qs = qs.filter(symbol__in=wanted)
    else:
        refresh_all()
    return Response(InstrumentSerializer(qs, many=True).data)


@api_view(["GET"])
def instrument_detail(request, symbol):
    inst = get_object_or_404(Instrument, symbol=symbol.upper(), is_active=True)
    tick(inst)
    data = InstrumentDetailSerializer(inst).data
    stats = instrument_stats(inst)
    for k in OPINION_KEYS:
        stats.pop(k, None)
    data["stats"] = stats
    return Response(data)


@api_view(["GET"])
def instrument_candles(request, symbol):
    inst = get_object_or_404(Instrument, symbol=symbol.upper(), is_active=True)
    tick(inst)
    tf = request.query_params.get("tf", "5m")
    try:
        limit = max(50, min(int(request.query_params.get("limit", 600)), 2000))
    except ValueError:
        limit = 600
    return Response({
        "symbol": inst.symbol, "tf": tf if tf in TIMEFRAMES else "5m", "timeframes": TIMEFRAMES,
        "candles": candles(inst, tf, limit),
        "quote": InstrumentSerializer(inst).data,
        "tz_offset": int(timezone.localtime().utcoffset().total_seconds()),
    })


@api_view(["GET"])
def instrument_news(request, symbol):
    inst = get_object_or_404(Instrument, symbol=symbol.upper(), is_active=True)
    return Response(get_news(inst.news_query or inst.name, inst.symbol))


@api_view(["GET"])
def market_news(request):
    return Response(get_news("Wall Street bolsa mercados acciones"))


@api_view(["GET"])
def instrument_history(request, symbol):
    inst = get_object_or_404(Instrument, symbol=symbol.upper(), is_active=True)
    tick(inst)
    range_key = request.query_params.get("range", "1A").upper()
    if range_key not in RANGES:
        range_key = "1A"
    return Response({"symbol": inst.symbol, "range": range_key, "bars": history_payload(inst, range_key)})


@api_view(["GET"])
def overview(request):
    refresh_all()
    insts = list(Instrument.objects.filter(is_active=True))
    by_change = sorted(insts, key=lambda i: i.change_pct, reverse=True)
    bench = next((i for i in insts if i.symbol == BENCHMARK_SYMBOL), None)
    advancing = sum(1 for i in insts if i.change_pct > 0)
    sectors = {}
    for i in insts:
        sectors.setdefault(i.sector, []).append(i.change_pct)
    return Response({
        "benchmark": InstrumentSerializer(bench).data if bench else None,
        "gainers": InstrumentSerializer(by_change[:5], many=True).data,
        "losers": InstrumentSerializer(list(reversed(by_change[-5:])), many=True).data,
        "breadth": {"advancing": advancing, "declining": len(insts) - advancing, "total": len(insts)},
        "sectors": sorted(
            [{"sector": s, "change_pct": round(sum(v) / len(v), 2), "count": len(v)} for s, v in sectors.items()],
            key=lambda x: x["change_pct"], reverse=True,
        ),
        "sector_list": sorted(sectors.keys()),
    })
