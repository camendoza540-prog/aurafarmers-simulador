from django.contrib import admin

from .models import Holding, Portfolio, PortfolioSnapshot, Position, Transaction


class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 0
    readonly_fields = ("instrument", "quantity", "avg_cost", "opened_at")


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "cash", "net_contributions", "created_at")
    search_fields = ("name", "user__username")
    inlines = [HoldingInline]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "portfolio", "type", "instrument", "quantity", "price", "fee", "total", "realized_pnl")
    list_filter = ("type", "instrument")
    search_fields = ("portfolio__name", "portfolio__user__username")


@admin.register(PortfolioSnapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "timestamp", "total_value", "cash", "invested_value")
    list_filter = ("portfolio",)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("opened_at", "portfolio", "instrument", "side", "quantity", "leverage", "entry_price",
                    "margin", "take_profit", "stop_loss", "status", "close_reason", "realized_pnl")
    list_filter = ("status", "side", "close_reason", "leverage")
