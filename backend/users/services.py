"""Cálculos agregados del usuario: patrimonio neto y ranking."""
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction


def net_worth(user) -> dict:
    from portfolios.services import valuate_portfolio
    from savings.services import account_value

    profile = user.profile
    portfolios_total = Decimal("0")
    for p in user.portfolios.prefetch_related("holdings__instrument"):
        portfolios_total += valuate_portfolio(p, record=False)["total_value"]
    savings_total = Decimal("0")
    for acc in user.savings_accounts.filter(status="active"):
        savings_total += account_value(acc)["value"]
    total = profile.cash_balance + portfolios_total + savings_total
    gain = total - profile.initial_balance
    pct = (gain / profile.initial_balance * 100) if profile.initial_balance else Decimal("0")
    return {
        "cash": profile.cash_balance,
        "portfolios": portfolios_total.quantize(Decimal("0.01")),
        "savings": savings_total.quantize(Decimal("0.01")),
        "total": total.quantize(Decimal("0.01")),
        "initial_balance": profile.initial_balance,
        "gain": gain.quantize(Decimal("0.01")),
        "gain_pct": pct.quantize(Decimal("0.01")),
    }


RANKING_TTL = 30  # segundos: calcular el patrimonio de todos los usuarios es costoso


def ranking(limit=10, me=None):
    """Usuarios ordenados por ganancia del patrimonio frente al saldo inicial (caché 30 s)."""
    from django.core.cache import cache

    rows = cache.get("ranking:all")
    if rows is None:
        stale = cache.get("ranking:stale")
        # Solo una petición recalcula; las demás usan la copia anterior mientras tanto
        if stale is not None and not cache.add("ranking:lock", 1, timeout=20):
            rows = stale
        else:
            rows = _compute_ranking()
            cache.set("ranking:all", rows, RANKING_TTL)
            cache.set("ranking:stale", rows, 3600)
            cache.delete("ranking:lock")
    rows = [dict(r, is_me=me is not None and r["user_id"] == me.pk) for r in rows]
    visible = [r for r in rows if r["show"] or r["is_me"]]
    for i, r in enumerate(visible, start=1):
        r["position"] = i
    top = visible[:limit]
    if me is not None and not any(r["is_me"] for r in top):
        mine = next((r for r in visible if r["is_me"]), None)
        if mine:
            top.append(mine)
    return top


def _compute_ranking():
    from portfolios.models import Position, Transaction

    User = get_user_model()
    rows = []
    users = User.objects.filter(is_active=True, is_superuser=False, is_staff=False).select_related("profile")
    for u in users:
        nw = net_worth(u)
        rows.append({
            "user_id": u.id,
            "username": u.username,
            "name": (u.get_full_name() or u.username).strip(),
            "avatar_url": u.profile.avatar.url if u.profile.avatar else None,
            "show": u.profile.show_in_ranking,
            "total": nw["total"],
            "profit": nw["gain"],
            "gain_pct": nw["gain_pct"],
            "trades": Transaction.objects.filter(portfolio__user=u, type__in=["BUY", "SELL", "CFD_OPEN"]).count(),
            "wins": Position.objects.filter(portfolio__user=u, status="CLOSED", realized_pnl__gt=0).count()
                    + Transaction.objects.filter(portfolio__user=u, type="SELL", realized_pnl__gt=0).count(),
        })
    rows.sort(key=lambda r: r["profit"], reverse=True)
    return rows


@transaction.atomic
def reset_simulation(user):
    """Reinicia la simulación: borra portafolios, ahorros y escenarios; restaura el saldo."""
    user.portfolios.all().delete()
    user.savings_accounts.all().delete()
    user.scenario_runs.all().delete()
    profile = user.profile
    profile.initial_balance = settings.SIMULATION["INITIAL_BALANCE"]
    profile.cash_balance = settings.SIMULATION["INITIAL_BALANCE"]
    profile.save()
