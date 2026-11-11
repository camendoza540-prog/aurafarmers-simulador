from django.contrib import admin

from .models import Instrument, IntradayBar, PriceBar


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("symbol", "name", "type", "sector", "current_price", "previous_close",
                    "annual_drift", "annual_volatility", "beta", "data_source", "is_active")
    list_filter = ("type", "asset_class", "sector", "data_source", "is_active")
    search_fields = ("symbol", "name")
    list_editable = ("is_active",)


@admin.register(PriceBar)
class PriceBarAdmin(admin.ModelAdmin):
    list_display = ("instrument", "date", "open", "high", "low", "close", "volume")
    list_filter = ("instrument",)
    date_hierarchy = "date"


@admin.register(IntradayBar)
class IntradayBarAdmin(admin.ModelAdmin):
    list_display = ("instrument", "ts", "open", "high", "low", "close", "volume")
    list_filter = ("instrument",)
