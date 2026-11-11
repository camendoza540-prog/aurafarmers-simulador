from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from portfolios.models import Portfolio
from portfolios.services import refresh_portfolio_prices, valuate_portfolio

from .engine import run_simulation
from .models import ScenarioRun
from .presets import PRESETS
from .serializers import ScenarioParamsSerializer, ScenarioRunSerializer


@api_view(["GET"])
def presets(request):
    return Response(PRESETS)


@api_view(["POST"])
def simulate(request):
    s = ScenarioParamsSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    params = dict(s.validated_data)
    portfolio = get_object_or_404(Portfolio, pk=params.pop("portfolio_id"), user=request.user)
    preset = params.pop("preset")
    seed = params.pop("seed")
    refresh_portfolio_prices(portfolio)
    valuation = valuate_portfolio(portfolio, record=False)
    if not valuation["holdings"] and not valuation["margin"]["open_positions"]:
        return Response(
            {"detail": "Este portafolio no tiene inversiones. Compra al menos un instrumento para simular escenarios."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    result = run_simulation(portfolio, valuation, params, seed)
    run = ScenarioRun.objects.create(
        user=request.user, portfolio=portfolio, portfolio_name=portfolio.name,
        preset=preset, params=params, summary=result["summary"],
    )
    result["run_id"] = run.id
    result["params"] = params
    return Response(result)


@api_view(["GET"])
def history(request):
    qs = ScenarioRun.objects.filter(user=request.user)[:20]
    return Response(ScenarioRunSerializer(qs, many=True).data)


@api_view(["DELETE"])
def delete_run(request, pk):
    get_object_or_404(ScenarioRun, pk=pk, user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
