from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from savings.services import savings_summary
from users.services import net_worth, ranking

from market.services.engine import refresh_open_positions, refresh_symbols

from .models import Holding, Portfolio, Position, Transaction
from .serializers import (
    AmountSerializer, OpenPositionSerializer, PortfolioSerializer, ProtectionSerializer, TradeSerializer,
    TransactionSerializer,
)
from .trading import (
    LEVERAGE_OPTIONS, TradingError, close_position, margin_status, open_position, position_payload,
    set_holding_protection, update_protection,
)
from .services import (
    TradeError, allocation, backtest, close_portfolio, create_portfolio, deposit, execute_trade,
    insights, refresh_portfolio_prices, risk_metrics, snapshot_series, valuate_portfolio, withdraw,
)
from config.formatting import usd


def _error(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user).prefetch_related("holdings__instrument")

    def list(self, request, *args, **kwargs):
        out = []
        for p in self.get_queryset():
            refresh_portfolio_prices(p)
            v = valuate_portfolio(p)
            data = PortfolioSerializer(p, context={"request": request}).data
            data.update({k: v[k] for k in ("total_value", "invested_value", "total_return", "total_return_pct",
                                           "day_change", "day_change_pct")})
            data["positions"] = len(v["holdings"])
            data["cfd_positions"] = v["margin"]["open_positions"]
            data["margin_level"] = v["margin"]["margin_level"]
            data["top_holdings"] = [h["symbol"] for h in v["holdings"][:4]]
            out.append(data)
        return Response(out)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            p = create_portfolio(
                request.user, s.validated_data["name"], s.validated_data.get("initial_deposit") or 0,
                s.validated_data.get("description", ""), s.validated_data.get("color", "pine"),
            )
        except TradeError as e:
            return _error(e)
        return Response(PortfolioSerializer(p, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        p = self.get_object()
        refresh_portfolio_prices(p)
        v = valuate_portfolio(p)
        risk = risk_metrics(p, v)
        data = PortfolioSerializer(p, context={"request": request}).data
        data.update(v)
        data["allocation"] = allocation(v)
        data["risk"] = risk
        data["insights"] = insights(p, v, risk)
        data["open_positions"] = [position_payload(x) for x in p.positions.filter(status="OPEN").select_related("instrument", "portfolio")]
        return Response(data)

    def destroy(self, request, *args, **kwargs):
        p = self.get_object()
        try:
            returned = close_portfolio(p)
        except TradeError as e:
            return _error(e)
        return Response({"detail": f"Portafolio cerrado. Se devolvieron {usd(returned)} a tu cuenta principal."})

    @action(detail=True, methods=["post"])
    def trade(self, request, pk=None):
        p = self.get_object()
        s = TradeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            tx = execute_trade(p, **s.validated_data)
        except TradeError as e:
            return _error(e)
        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def positions(self, request, pk=None):
        p = self.get_object()
        if request.method == "GET":
            status_f = request.query_params.get("status", "OPEN").upper()
            qs = p.positions.filter(status=status_f).select_related("instrument", "portfolio")[:200]
            return Response([position_payload(x) for x in qs])
        s = OpenPositionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            pos = open_position(p, **s.validated_data)
        except TradingError as e:
            return _error(e)
        return Response(position_payload(pos), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"holdings/(?P<symbol>[A-Za-z0-9.\-]+)/protection")
    def holding_protection(self, request, pk=None, symbol=None):
        p = self.get_object()
        holding = p.holdings.select_related("instrument").filter(instrument__symbol=symbol.upper()).first()
        if not holding:
            return Response({"detail": "No tienes esa posición."}, status=status.HTTP_404_NOT_FOUND)
        s = ProtectionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            set_holding_protection(holding, s.validated_data.get("take_profit"), s.validated_data.get("stop_loss"))
        except TradingError as e:
            return _error(e)
        return Response({"symbol": symbol.upper(), "take_profit": holding.take_profit, "stop_loss": holding.stop_loss})

    @action(detail=True, methods=["post"])
    def deposit(self, request, pk=None):
        p = self.get_object()
        s = AmountSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            tx = deposit(p, s.validated_data["amount"])
        except TradeError as e:
            return _error(e)
        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        p = self.get_object()
        s = AmountSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            tx = withdraw(p, s.validated_data["amount"])
        except TradeError as e:
            return _error(e)
        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        p = self.get_object()
        qs = p.transactions.select_related("instrument", "portfolio")[:200]
        return Response(TransactionSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        p = self.get_object()
        days = {"1M": 31, "3M": 92, "6M": 183, "1A": 365, "2A": 730}.get(request.query_params.get("range", "1A").upper(), 365)
        return Response({"snapshots": snapshot_series(p), "backtest": backtest(p, days)})


@api_view(["GET"])
def dashboard(request):
    user = request.user
    portfolios = []
    for p in user.portfolios.prefetch_related("holdings__instrument"):
        refresh_portfolio_prices(p)
        v = valuate_portfolio(p)
        portfolios.append({
            "id": p.id, "name": p.name, "color": p.color,
            "total_value": v["total_value"], "total_return_pct": v["total_return_pct"],
            "day_change_pct": v["day_change_pct"], "positions": len(v["holdings"]),
            "cfd_positions": v["margin"]["open_positions"],
        })
    recent = Transaction.objects.filter(portfolio__user=user).select_related("instrument", "portfolio")[:8]
    return Response({
        "net_worth": net_worth(user),
        "portfolios": portfolios,
        "savings": savings_summary(user),
        "recent_transactions": TransactionSerializer(recent, many=True).data,
        "ranking": ranking(5, me=user),
        "lessons_completed": user.lesson_progress.count(),
    })


@api_view(["GET"])
def all_positions(request):
    """Posiciones CFD del usuario en todos sus portafolios (filtros: status, symbol)."""
    refresh_open_positions()
    qs = Position.objects.filter(portfolio__user=request.user).select_related("instrument", "portfolio")
    qs = qs.filter(status=request.query_params.get("status", "OPEN").upper())
    sym = request.query_params.get("symbol")
    if sym:
        qs = qs.filter(instrument__symbol=sym.upper())
    return Response([position_payload(x) for x in qs[:200]])


def _own_position(request, pk):
    return get_object_or_404(Position.objects.select_related("instrument", "portfolio"), pk=pk, portfolio__user=request.user)


@api_view(["PATCH"])
def position_protection(request, pk):
    pos = _own_position(request, pk)
    s = ProtectionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    try:
        update_protection(pos, s.validated_data.get("take_profit"), s.validated_data.get("stop_loss"))
    except TradingError as e:
        return _error(e)
    return Response(position_payload(pos))


@api_view(["POST"])
def position_close(request, pk):
    pos = _own_position(request, pk)
    refresh_symbols([pos.instrument.symbol])
    pos.refresh_from_db()
    try:
        pos = close_position(pos, "MANUAL")
    except TradingError as e:
        return _error(e)
    return Response(position_payload(pos))


@api_view(["GET"])
def trading_account(request):
    """Resumen para el terminal: efectivo y margen de cada portafolio, y reglas de apalancamiento."""
    refresh_open_positions()
    rows = []
    for p in request.user.portfolios.all():
        m = margin_status(p)
        holdings = {h.instrument.symbol: {"quantity": h.quantity, "avg_cost": h.avg_cost,
                                          "take_profit": h.take_profit, "stop_loss": h.stop_loss}
                    for h in p.holdings.select_related("instrument")}
        rows.append({"id": p.id, "name": p.name, "color": p.color, "cash": p.cash, "margin": m, "holdings": holdings})
    from django.conf import settings
    return Response({
        "portfolios": rows,
        "leverage_options": LEVERAGE_OPTIONS,
        "commission_rate": float(settings.SIMULATION["COMMISSION_RATE"]),
        "min_commission": float(settings.SIMULATION["MIN_COMMISSION"]),
        "stop_out_level": settings.SIMULATION["STOP_OUT_LEVEL"],
        "margin_call_level": settings.SIMULATION["MARGIN_CALL_LEVEL"],
    })


@api_view(["GET"])
def all_transactions(request):
    qs = Transaction.objects.filter(portfolio__user=request.user).select_related("instrument", "portfolio")
    t = request.query_params.get("type")
    if t:
        qs = qs.filter(type=t.upper())
    return Response(TransactionSerializer(qs[:300], many=True).data)
