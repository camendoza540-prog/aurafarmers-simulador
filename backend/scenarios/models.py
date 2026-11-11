from django.conf import settings
from django.db import models


class ScenarioRun(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scenario_runs")
    portfolio = models.ForeignKey("portfolios.Portfolio", on_delete=models.SET_NULL, null=True, blank=True, related_name="scenario_runs")
    portfolio_name = models.CharField(max_length=60)
    preset = models.CharField(max_length=30, default="custom")
    params = models.JSONField()
    summary = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Simulación de escenario"
        verbose_name_plural = "Simulaciones de escenarios"

    def __str__(self):
        return f"{self.preset} · {self.portfolio_name} · {self.created_at:%Y-%m-%d %H:%M}"
