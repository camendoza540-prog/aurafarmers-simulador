from rest_framework import serializers

from .models import ScenarioRun


class ScenarioParamsSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    preset = serializers.CharField(max_length=30, default="custom")
    market_shock = serializers.FloatField(min_value=-80, max_value=80, default=0, help_text="% de choque al mercado")
    shock_days = serializers.IntegerField(min_value=0, max_value=756, default=0)
    recovery = serializers.FloatField(min_value=0, max_value=100, default=0, help_text="% de la caída que se recupera")
    volatility_multiplier = serializers.FloatField(min_value=0.2, max_value=4, default=1)
    rate_change = serializers.FloatField(min_value=-10, max_value=10, default=0, help_text="cambio de tasas en puntos")
    drift_adjustment = serializers.FloatField(min_value=-30, max_value=30, default=0, help_text="puntos de rendimiento anual")
    horizon_days = serializers.IntegerField(min_value=21, max_value=1260, default=252)
    seed = serializers.IntegerField(required=False, default=2026)


class ScenarioRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioRun
        fields = ["id", "portfolio", "portfolio_name", "preset", "params", "summary", "created_at"]
