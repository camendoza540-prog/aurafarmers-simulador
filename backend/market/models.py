from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models


class Instrument(models.Model):
    """Instrumento financiero negociable en el simulador (acción o ETF)."""

    TYPE_CHOICES = [
        ("STOCK", "Acción"), ("ETF", "ETF"), ("FOREX", "Divisa"),
        ("INDEX", "Índice"), ("COMMODITY", "Materia prima"), ("CRYPTO", "Criptomoneda"),
    ]
    ASSET_CLASS_CHOICES = [
        ("equity", "Renta variable"),
        ("bond", "Renta fija"),
        ("commodity", "Materias primas"),
        ("real_estate", "Inmobiliario"),
        ("forex", "Divisas"),
        ("crypto", "Criptomonedas"),
    ]
    # Solo se negocian como CFD (no se compran «de contado»), igual que en XTB o IQ Option
    CFD_ONLY_TYPES = {"FOREX", "INDEX", "COMMODITY", "CRYPTO"}

    symbol = models.CharField("Símbolo", max_length=12, unique=True)
    name = models.CharField("Nombre", max_length=120)
    type = models.CharField("Tipo", max_length=10, choices=TYPE_CHOICES)
    asset_class = models.CharField("Clase de activo", max_length=16, choices=ASSET_CLASS_CHOICES, default="equity")
    sector = models.CharField("Sector", max_length=60)
    country = models.CharField("País", max_length=40, default="Estados Unidos")
    currency = models.CharField("Moneda", max_length=3, default="USD")
    description = models.TextField("Descripción", blank=True)
    news_query = models.CharField("Búsqueda de noticias", max_length=120, blank=True)
    # Divisas: el precio se expresa en la moneda cotizada (USDJPY → yenes por dólar)
    base_currency = models.CharField("Moneda base", max_length=3, blank=True)
    quote_currency = models.CharField("Moneda cotizada", max_length=3, default="USD")
    leverage_cap = models.PositiveSmallIntegerField("Apalancamiento máximo", null=True, blank=True)
    spread = models.FloatField("Spread (fracción del precio)", null=True, blank=True)

    # Parámetros del modelo de precios (movimiento browniano geométrico con factor de mercado)
    anchor_price = models.DecimalField("Precio de referencia", max_digits=14, decimal_places=4)
    annual_drift = models.FloatField("Rendimiento esperado anual (μ)")
    annual_volatility = models.FloatField("Volatilidad anual (σ)")
    beta = models.FloatField("Beta frente al mercado", default=1.0)
    duration = models.FloatField("Duración (renta fija)", default=0.0)
    base_volume = models.PositiveIntegerField("Volumen base diario", default=1_000_000)

    # Estado de la cotización
    current_price = models.DecimalField("Precio actual", max_digits=14, decimal_places=4, default=0)
    previous_close = models.DecimalField("Cierre anterior", max_digits=14, decimal_places=4, default=0)
    last_tick_at = models.DateTimeField("Última actualización", null=True, blank=True)
    history_synced_on = models.DateField(null=True, blank=True)
    data_source = models.CharField("Fuente de datos", max_length=20, default="simulado")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["type", "symbol"]
        verbose_name = "Instrumento"
        verbose_name_plural = "Instrumentos"

    def __str__(self):
        return f"{self.symbol} — {self.name}"

    @property
    def change(self):
        return self.current_price - self.previous_close

    @property
    def change_pct(self):
        if not self.previous_close:
            return 0.0
        return float((self.current_price / self.previous_close - 1) * 100)

    # ── Trading con margen ────────────────────────────────────────────────
    @property
    def cfd_only(self) -> bool:
        return self.type in self.CFD_ONLY_TYPES

    @property
    def max_leverage(self) -> int:
        if self.leverage_cap:
            return self.leverage_cap
        if self.type in ("STOCK", "ETF"):
            return 5  # ESMA: acciones y ETF, 1:5
        return settings.SIMULATION["MAX_LEVERAGE"].get(self.asset_class, 5)

    @property
    def spread_pct(self) -> float:
        if self.spread is not None:
            return self.spread
        return settings.SIMULATION["SPREAD"].get(self.asset_class, 0.0006)

    def usd_factor(self, price=None) -> Decimal:
        """Convierte importes de la moneda cotizada a USD (USDJPY: 1/precio)."""
        if self.quote_currency == "USD":
            return Decimal("1")
        p = Decimal(str(price if price is not None else self.current_price))
        return Decimal("1") / p if p else Decimal("1")

    def _half_spread(self) -> Decimal:
        return self.current_price * Decimal(str(self.spread_pct / 2))

    @property
    def bid(self) -> Decimal:
        """Precio al que el mercado te compra (vendes / cierras un largo)."""
        return (self.current_price - self._half_spread()).quantize(Decimal("0.0001"), ROUND_HALF_UP)

    @property
    def ask(self) -> Decimal:
        """Precio al que el mercado te vende (compras / cierras un corto)."""
        return (self.current_price + self._half_spread()).quantize(Decimal("0.0001"), ROUND_HALF_UP)


class PriceBar(models.Model):
    """Barra diaria OHLCV."""

    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="bars")
    date = models.DateField(db_index=True)
    open = models.DecimalField(max_digits=14, decimal_places=4)
    high = models.DecimalField(max_digits=14, decimal_places=4)
    low = models.DecimalField(max_digits=14, decimal_places=4)
    close = models.DecimalField(max_digits=14, decimal_places=4)
    volume = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["date"]
        unique_together = ("instrument", "date")
        verbose_name = "Barra de precio"
        verbose_name_plural = "Historial de precios"

    def __str__(self):
        return f"{self.instrument.symbol} {self.date} {self.close}"


class IntradayBar(models.Model):
    """Vela de 1 minuto (reloj real) para los gráficos intradía."""

    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="intraday")
    ts = models.DateTimeField("Inicio del minuto", db_index=True)
    open = models.DecimalField(max_digits=14, decimal_places=4)
    high = models.DecimalField(max_digits=14, decimal_places=4)
    low = models.DecimalField(max_digits=14, decimal_places=4)
    close = models.DecimalField(max_digits=14, decimal_places=4)
    volume = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["ts"]
        unique_together = ("instrument", "ts")
        verbose_name = "Vela de 1 minuto"
        verbose_name_plural = "Velas de 1 minuto"
