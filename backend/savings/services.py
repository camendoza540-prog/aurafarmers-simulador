"""Interés compuesto, productos de ahorro (CDT y cuenta) y calculadora."""
import math
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from users.models import InsufficientFunds

from .models import SavingsAccount
from .products import PRODUCTS
from config.formatting import usd

Q2 = Decimal("0.01")


class SavingsError(Exception):
    pass


def _elapsed_days(acc: SavingsAccount, since_base=True) -> float:
    now = acc.closed_at or timezone.now()
    ref = acc.base_at if since_base else acc.opened_at
    real = (now - ref).total_seconds() / 86400
    sim = acc.simulated_days - (acc.base_sim_days if since_base else 0)
    return max(real, 0) + sim


def account_value(acc: SavingsAccount) -> dict:
    total_days = _elapsed_days(acc, since_base=False)
    if acc.status == "closed":
        value = acc.final_value or Decimal("0")
    else:
        days = _elapsed_days(acc, since_base=True)
        if acc.term_days:
            days = min(days, acc.term_days)  # el CDT deja de rentar al vencer (no admite aportes)
        value = Decimal(str(float(acc.base_amount) * (1 + float(acc.rate_ea)) ** (days / 365))).quantize(Q2, ROUND_HALF_UP)
    matured = bool(acc.term_days) and total_days >= acc.term_days
    rate = float(acc.rate_ea)
    at_maturity = None
    maturity_date = None
    if acc.term_days:
        at_maturity = Decimal(str(float(acc.principal) * (1 + rate) ** (acc.term_days / 365))).quantize(Q2)
        remaining = max(acc.term_days - total_days, 0)
        maturity_date = (timezone.localdate() + timedelta(days=round(remaining))).isoformat()
    one_year = Decimal(str(float(value) * (1 + rate))).quantize(Q2)
    return {
        "value_at_maturity": at_maturity,
        "maturity_date": maturity_date,
        "progress_pct": round(min(total_days / acc.term_days, 1) * 100, 1) if acc.term_days else None,
        "daily_interest": Decimal(str(float(value) * ((1 + rate) ** (1 / 365) - 1))).quantize(Q2),
        "value_in_one_year": one_year,
        "value": value,
        "interest": (value - acc.principal).quantize(Q2),
        "days_elapsed": round(total_days, 2),
        "days_to_maturity": max(0, round(acc.term_days - total_days, 1)) if acc.term_days else None,
        "matured": matured,
        "can_withdraw": acc.status == "active" and (acc.term_days is None or matured),
    }


@transaction.atomic
def open_account(user, product_code: str, amount: Decimal, name: str | None = None) -> SavingsAccount:
    product = PRODUCTS.get(product_code)
    if not product:
        raise SavingsError("Producto de ahorro no válido.")
    amount = Decimal(amount).quantize(Q2)
    if amount < product["min_amount"]:
        raise SavingsError(f"El monto mínimo para {product['name']} es {usd(product['min_amount'])}.")
    try:
        user.profile.debit(amount)
    except InsufficientFunds as exc:
        raise SavingsError(str(exc)) from exc
    return SavingsAccount.objects.create(
        user=user, name=(name or product["name"])[:60], product=product_code,
        rate_ea=product["rate_ea"], term_days=product["term_days"],
        principal=amount, base_amount=amount, base_at=timezone.now(),
    )


@transaction.atomic
def deposit_to_account(acc: SavingsAccount, amount: Decimal):
    if acc.term_days:
        raise SavingsError("A un CDT no se le pueden hacer aportes adicionales; abre uno nuevo.")
    if acc.status != "active":
        raise SavingsError("La cuenta está cerrada.")
    amount = Decimal(amount).quantize(Q2)
    if amount <= 0:
        raise SavingsError("El monto debe ser mayor que cero.")
    try:
        acc.user.profile.debit(amount)
    except InsufficientFunds as exc:
        raise SavingsError(str(exc)) from exc
    current = account_value(acc)["value"]
    acc.base_amount = current + amount
    acc.base_at = timezone.now()
    acc.base_sim_days = acc.simulated_days
    acc.principal += amount
    acc.save()


def advance_time(acc: SavingsAccount, days: int):
    if acc.status != "active":
        raise SavingsError("La cuenta está cerrada.")
    if days <= 0 or days > 3650:
        raise SavingsError("Puedes avanzar entre 1 y 3650 días.")
    acc.simulated_days += days
    acc.save(update_fields=["simulated_days"])


@transaction.atomic
def close_account(acc: SavingsAccount) -> Decimal:
    info = account_value(acc)
    if acc.status != "active":
        raise SavingsError("La cuenta ya está cerrada.")
    if not info["can_withdraw"]:
        raise SavingsError(
            f"Un CDT no se puede redimir antes del vencimiento. Faltan {info['days_to_maturity']:.0f} días; "
            "usa «Avanzar tiempo» para simular el paso de los días."
        )
    value = info["value"]
    acc.final_value = value
    acc.status = "closed"
    acc.closed_at = timezone.now()
    acc.save()
    acc.user.profile.credit(value)
    return value


@transaction.atomic
def renew_account(acc: SavingsAccount) -> SavingsAccount:
    """Renueva un CDT vencido: lo redime y abre otro igual con capital + intereses."""
    if not acc.term_days:
        raise SavingsError("Solo los CDT se renuevan.")
    value = close_account(acc)
    return open_account(acc.user, acc.product, value, name=acc.name)


def projection(acc: SavingsAccount, points=24):
    """Curva de crecimiento esperado de la cuenta (para graficar)."""
    horizon = acc.term_days or 365 * 5
    rate = float(acc.rate_ea)
    principal = float(acc.principal)
    step = max(horizon // points, 1)
    return [
        {"day": d, "value": round(principal * (1 + rate) ** (d / 365), 2)}
        for d in range(0, horizon + 1, step)
    ]


def savings_summary(user) -> dict:
    active = user.savings_accounts.filter(status="active")
    total = principal = Decimal("0")
    for acc in active:
        v = account_value(acc)
        total += v["value"]
        principal += acc.principal
    return {"accounts": active.count(), "value": total, "principal": principal, "interest": (total - principal).quantize(Q2)}


# ── Calculadora ──────────────────────────────────────────────────────────

def nominal_to_ea(nominal: float, periods: int) -> float:
    return (1 + nominal / periods) ** periods - 1


def ea_to_nominal(ea: float, periods: int) -> float:
    return periods * ((1 + ea) ** (1 / periods) - 1)


def calculator(initial: float, monthly: float, rate: float, years: int, rate_type="EA",
               periods_per_year=12, inflation=0.0) -> dict:
    ea = rate if rate_type == "EA" else nominal_to_ea(rate, periods_per_year)
    i_m = (1 + ea) ** (1 / 12) - 1
    balance = initial
    simple = initial
    contributed = initial
    rows = [{"year": 0, "balance": round(initial, 2), "contributed": round(initial, 2), "interest": 0.0,
             "simple": round(initial, 2), "real": round(initial, 2)}]
    for m in range(1, years * 12 + 1):
        balance = balance * (1 + i_m) + monthly
        simple += contributed * ea / 12 + monthly
        contributed += monthly
        if m % 12 == 0:
            y = m // 12
            rows.append({
                "year": y,
                "balance": round(balance, 2),
                "contributed": round(contributed, 2),
                "interest": round(balance - contributed, 2),
                "simple": round(simple, 2),
                "real": round(balance / (1 + inflation) ** y, 2),
            })
    double_years = math.log(2) / math.log(1 + ea) if ea > 0 else None
    return {
        "effective_annual": round(ea * 100, 4),
        "nominal_monthly_equivalent": round(ea_to_nominal(ea, 12) * 100, 4),
        "monthly_rate": round(i_m * 100, 4),
        "final_balance": round(balance, 2),
        "total_contributed": round(contributed, 2),
        "total_interest": round(balance - contributed, 2),
        "final_simple": round(simple, 2),
        "compound_advantage": round(balance - simple, 2),
        "final_real": round(balance / (1 + inflation) ** years, 2),
        "years_to_double": round(double_years, 1) if double_years else None,
        "rule_of_72": round(72 / (ea * 100), 1) if ea > 0 else None,
        "rows": rows,
    }
