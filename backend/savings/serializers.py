from rest_framework import serializers

from .models import SavingsAccount
from .products import PRODUCTS
from .services import account_value, projection


class SavingsAccountSerializer(serializers.ModelSerializer):
    product_label = serializers.CharField(source="get_product_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    current = serializers.SerializerMethodField()
    projection = serializers.SerializerMethodField()

    class Meta:
        model = SavingsAccount
        fields = ["id", "name", "product", "product_label", "rate_ea", "term_days", "principal",
                  "simulated_days", "status", "status_label", "opened_at", "closed_at", "final_value",
                  "current", "projection"]

    def get_current(self, obj):
        return account_value(obj)

    def get_projection(self, obj):
        return projection(obj)


class OpenAccountSerializer(serializers.Serializer):
    product = serializers.ChoiceField(choices=list(PRODUCTS.keys()))
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=1)
    name = serializers.CharField(max_length=60, required=False, allow_blank=True)


class CalculatorSerializer(serializers.Serializer):
    initial = serializers.FloatField(min_value=0, max_value=1e10)
    monthly = serializers.FloatField(min_value=0, max_value=1e9, default=0)
    rate = serializers.FloatField(min_value=0, max_value=100, help_text="Tasa en porcentaje, p. ej. 9.5")
    years = serializers.IntegerField(min_value=1, max_value=60)
    rate_type = serializers.ChoiceField(choices=["EA", "NOMINAL"], default="EA")
    periods_per_year = serializers.ChoiceField(choices=[1, 2, 4, 12, 365], default=12)
    inflation = serializers.FloatField(min_value=0, max_value=100, default=5.0)
