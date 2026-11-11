from rest_framework import serializers

from .models import Instrument
from .services.stats import sparkline


class InstrumentSerializer(serializers.ModelSerializer):
    change = serializers.SerializerMethodField()
    change_pct = serializers.SerializerMethodField()
    bid = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    ask = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    max_leverage = serializers.IntegerField(read_only=True)
    spread_pct = serializers.FloatField(read_only=True)
    cfd_only = serializers.BooleanField(read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    asset_class_label = serializers.CharField(source="get_asset_class_display", read_only=True)

    class Meta:
        model = Instrument
        fields = [
            "symbol", "name", "type", "type_label", "asset_class", "asset_class_label", "sector",
            "country", "currency", "current_price", "previous_close", "change", "change_pct",
            "bid", "ask", "max_leverage", "spread_pct", "cfd_only", "base_currency", "quote_currency",
            "last_tick_at", "data_source",
        ]

    def get_change(self, obj):
        return round(float(obj.change), 4)

    def get_change_pct(self, obj):
        return round(obj.change_pct, 2)


class InstrumentListSerializer(InstrumentSerializer):
    sparkline = serializers.SerializerMethodField()

    class Meta(InstrumentSerializer.Meta):
        fields = InstrumentSerializer.Meta.fields + ["sparkline"]

    def get_sparkline(self, obj):
        return sparkline(obj, 30)


class InstrumentDetailSerializer(InstrumentSerializer):
    class Meta(InstrumentSerializer.Meta):
        fields = InstrumentSerializer.Meta.fields + [
            "description", "annual_drift", "annual_volatility", "beta", "duration",
        ]
