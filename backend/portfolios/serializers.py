from rest_framework import serializers

from .models import Portfolio, Transaction
from .trading import LEVERAGE_OPTIONS


class PortfolioSerializer(serializers.ModelSerializer):
    initial_deposit = serializers.DecimalField(max_digits=18, decimal_places=2, write_only=True, required=False, min_value=0)

    class Meta:
        model = Portfolio
        fields = ["id", "name", "description", "color", "cash", "net_contributions", "created_at", "initial_deposit"]
        read_only_fields = ["id", "cash", "net_contributions", "created_at"]

    def validate_name(self, value):
        value = value.strip()
        user = self.context["request"].user
        qs = Portfolio.objects.filter(user=user, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya tienes un portafolio con ese nombre.")
        return value


class TransactionSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="instrument.symbol", default=None, read_only=True)
    instrument_name = serializers.CharField(source="instrument.name", default=None, read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    portfolio_name = serializers.CharField(source="portfolio.name", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "type", "type_label", "symbol", "instrument_name", "portfolio", "portfolio_name",
                  "quantity", "price", "fee", "total", "realized_pnl", "cash_after", "note", "position", "created_at"]


class TradeSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    side = serializers.ChoiceField(choices=["BUY", "SELL"])
    quantity = serializers.DecimalField(max_digits=20, decimal_places=6, required=False, allow_null=True, min_value=0)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True, min_value=0)
    take_profit = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)
    stop_loss = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("quantity") and not attrs.get("amount"):
            raise serializers.ValidationError("Indica una cantidad de unidades o un monto en USD.")
        return attrs


class AmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=0)


class OpenPositionSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    side = serializers.ChoiceField(choices=["LONG", "SHORT"])
    leverage = serializers.IntegerField(min_value=1, max_value=max(LEVERAGE_OPTIONS), default=1)
    quantity = serializers.DecimalField(max_digits=20, decimal_places=6, required=False, allow_null=True, min_value=0)
    margin_amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True, min_value=0)
    take_profit = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)
    stop_loss = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("quantity") and not attrs.get("margin_amount"):
            raise serializers.ValidationError("Indica unidades o el margen a invertir en USD.")
        return attrs


class ProtectionSerializer(serializers.Serializer):
    take_profit = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)
    stop_loss = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)
