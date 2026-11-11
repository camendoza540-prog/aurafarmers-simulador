from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SavingsAccount
from .products import PRODUCTS
from .serializers import CalculatorSerializer, OpenAccountSerializer, SavingsAccountSerializer
from .services import (
    SavingsError, advance_time, calculator, close_account, deposit_to_account, open_account, renew_account,
    savings_summary,
)
from config.formatting import usd


def _err(e):
    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def products(request):
    return Response([{**p, "rate_ea": float(p["rate_ea"]) * 100} for p in PRODUCTS.values()])


@api_view(["GET", "POST"])
def accounts(request):
    if request.method == "POST":
        s = OpenAccountSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            acc = open_account(request.user, s.validated_data["product"], s.validated_data["amount"], s.validated_data.get("name"))
        except SavingsError as e:
            return _err(e)
        return Response(SavingsAccountSerializer(acc).data, status=status.HTTP_201_CREATED)
    qs = SavingsAccount.objects.filter(user=request.user)
    return Response({
        "summary": savings_summary(request.user),
        "accounts": SavingsAccountSerializer(qs, many=True).data,
    })


def _acc(request, pk):
    return get_object_or_404(SavingsAccount, pk=pk, user=request.user)


@api_view(["POST"])
def advance(request, pk):
    acc = _acc(request, pk)
    try:
        advance_time(acc, int(request.data.get("days", 30)))
    except (SavingsError, ValueError) as e:
        return _err(e)
    return Response(SavingsAccountSerializer(acc).data)


@api_view(["POST"])
def deposit(request, pk):
    acc = _acc(request, pk)
    try:
        deposit_to_account(acc, request.data.get("amount", 0))
    except (SavingsError, ValueError, ArithmeticError) as e:
        return _err(e)
    return Response(SavingsAccountSerializer(acc).data)


@api_view(["POST"])
def withdraw(request, pk):
    acc = _acc(request, pk)
    try:
        value = close_account(acc)
    except SavingsError as e:
        return _err(e)
    return Response({"detail": f"Se acreditaron {usd(value)} a tu cuenta principal.",
                     "account": SavingsAccountSerializer(acc).data})


@api_view(["POST"])
def calc(request):
    s = CalculatorSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    return Response(calculator(
        d["initial"], d["monthly"], d["rate"] / 100, d["years"], d["rate_type"],
        int(d["periods_per_year"]), d["inflation"] / 100,
    ))


@api_view(["POST"])
def renew(request, pk):
    acc = _acc(request, pk)
    try:
        new = renew_account(acc)
    except SavingsError as e:
        return _err(e)
    return Response({"detail": f"CDT renovado por {usd(new.principal)}.", "account": SavingsAccountSerializer(new).data})
