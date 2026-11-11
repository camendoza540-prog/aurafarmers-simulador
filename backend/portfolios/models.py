from django.conf import settings
from django.db import models

from market.models import Instrument


class Portfolio(models.Model):
    COLOR_CHOICES = [
        ("pine", "Pino"), ("gold", "Trigo"), ("clay", "Arcilla"),
        ("sky", "Cielo"), ("plum", "Ciruela"), ("moss", "Musgo"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField("Nombre", max_length=60)
    description = models.CharField("Estrategia / descripción", max_length=240, blank=True)
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default="pine")
    cash = models.DecimalField("Efectivo del portafolio", max_digits=18, decimal_places=2, default=0)
    net_contributions = models.DecimalField("Aportes netos", max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ("user", "name")
        verbose_name = "Portafolio"
        verbose_name_plural = "Portafolios"

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="holdings")
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT, related_name="holdings")
    quantity = models.DecimalField("Cantidad", max_digits=20, decimal_places=6)
    avg_cost = models.DecimalField("Costo promedio", max_digits=14, decimal_places=4)
    take_profit = models.DecimalField("Take profit", max_digits=14, decimal_places=4, null=True, blank=True)
    stop_loss = models.DecimalField("Stop loss", max_digits=14, decimal_places=4, null=True, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("portfolio", "instrument")
        verbose_name = "Posición"
        verbose_name_plural = "Posiciones"

    def __str__(self):
        return f"{self.quantity} {self.instrument.symbol} en {self.portfolio.name}"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ("BUY", "Compra"), ("SELL", "Venta"),
        ("DEPOSIT", "Aporte"), ("WITHDRAW", "Retiro"),
        ("CFD_OPEN", "Apertura CFD"), ("CFD_CLOSE", "Cierre CFD"),
    ]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="transactions")
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT, null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    price = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("Monto total", max_digits=18, decimal_places=2)
    realized_pnl = models.DecimalField("Ganancia realizada", max_digits=18, decimal_places=2, null=True, blank=True)
    cash_after = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    note = models.CharField("Detalle", max_length=80, blank=True)
    position = models.ForeignKey("Position", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"

    def __str__(self):
        sym = self.instrument.symbol if self.instrument else ""
        return f"{self.get_type_display()} {sym} {self.total}"


class PortfolioSnapshot(models.Model):
    """Foto del valor del portafolio en un instante (para la gráfica de rendimiento)."""

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="snapshots")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    total_value = models.DecimalField(max_digits=18, decimal_places=2)
    cash = models.DecimalField(max_digits=18, decimal_places=2)
    invested_value = models.DecimalField(max_digits=18, decimal_places=2)
    net_contributions = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Snapshot"
        verbose_name_plural = "Snapshots"


class Position(models.Model):
    """
    Posición con margen (CFD): permite apalancamiento y operar en corto.

    Al abrir se bloquea el margen = valor nocional / apalancamiento. La ganancia o
    pérdida se calcula sobre el valor nocional completo, con precios bid/ask.
    """

    SIDE_CHOICES = [("LONG", "Compra (largo)"), ("SHORT", "Venta (corto)")]
    STATUS_CHOICES = [("OPEN", "Abierta"), ("CLOSED", "Cerrada")]
    REASON_CHOICES = [
        ("MANUAL", "Cierre manual"), ("TP", "Take profit"), ("SL", "Stop loss"),
        ("STOP_OUT", "Cierre forzoso por margen"), ("PORTFOLIO", "Cierre del portafolio"),
    ]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT, related_name="positions")
    side = models.CharField("Dirección", max_length=5, choices=SIDE_CHOICES)
    quantity = models.DecimalField("Unidades", max_digits=20, decimal_places=6)
    leverage = models.PositiveSmallIntegerField("Apalancamiento", default=1)
    entry_price = models.DecimalField("Precio de entrada", max_digits=14, decimal_places=4)
    notional = models.DecimalField("Valor nocional", max_digits=18, decimal_places=2)
    margin = models.DecimalField("Margen bloqueado", max_digits=18, decimal_places=2)
    take_profit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=6, choices=STATUS_CHOICES, default="OPEN", db_index=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    close_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    close_reason = models.CharField(max_length=10, choices=REASON_CHOICES, blank=True)
    realized_pnl = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-opened_at", "-id"]
        verbose_name = "Posición CFD"
        verbose_name_plural = "Posiciones CFD"

    def __str__(self):
        return f"{self.get_side_display()} {self.quantity} {self.instrument.symbol} x{self.leverage}"

    @property
    def direction(self) -> int:
        return 1 if self.side == "LONG" else -1

    def exit_price(self):
        """Precio al que se cerraría ahora: bid para largos, ask para cortos."""
        return self.instrument.bid if self.side == "LONG" else self.instrument.ask

    def unrealized_pnl(self):
        from decimal import Decimal
        exit_price = self.exit_price()
        return ((exit_price - self.entry_price) * self.quantity * self.direction
                * self.instrument.usd_factor(exit_price)).quantize(Decimal("0.01"))
