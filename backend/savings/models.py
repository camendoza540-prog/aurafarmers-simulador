from django.conf import settings
from django.db import models


class SavingsAccount(models.Model):
    """
    Cuenta de ahorro o CDT con interés compuesto.

    El valor se calcula como  V = base_amount · (1 + EA)^(días/365)
    donde los días = días reales transcurridos + días simulados ("avanzar tiempo").
    """

    TYPE_CHOICES = [
        ("AHORRO", "Cuenta de ahorro"), ("CDT90", "CDT 90 días"),
        ("CDT180", "CDT 180 días"), ("CDT360", "CDT 360 días"),
    ]
    STATUS_CHOICES = [("active", "Activa"), ("closed", "Cerrada")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="savings_accounts")
    name = models.CharField(max_length=60)
    product = models.CharField(max_length=10, choices=TYPE_CHOICES)
    rate_ea = models.DecimalField("Tasa efectiva anual", max_digits=7, decimal_places=5)
    term_days = models.PositiveIntegerField(null=True, blank=True)

    principal = models.DecimalField("Capital aportado", max_digits=18, decimal_places=2)
    base_amount = models.DecimalField(max_digits=18, decimal_places=6)
    base_at = models.DateTimeField()
    base_sim_days = models.PositiveIntegerField(default=0)
    simulated_days = models.PositiveIntegerField("Días simulados", default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    final_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["status", "-opened_at"]
        verbose_name = "Cuenta de ahorro / CDT"
        verbose_name_plural = "Cuentas de ahorro / CDT"

    def __str__(self):
        return f"{self.name} ({self.get_product_display()}) — {self.user.username}"
