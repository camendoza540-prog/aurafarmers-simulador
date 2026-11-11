from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F
from django.utils import timezone
from config.formatting import usd


class InsufficientFunds(ValueError):
    """El usuario no tiene efectivo suficiente en su cuenta principal."""


def default_initial_balance():
    return settings.SIMULATION["INITIAL_BALANCE"]


class Profile(models.Model):
    """Perfil del inversionista: saldo ficticio disponible y perfil de riesgo."""

    RISK_CHOICES = [
        ("conservador", "Conservador"),
        ("moderado", "Moderado"),
        ("agresivo", "Agresivo"),
    ]
    EXPERIENCE_CHOICES = [
        ("ninguna", "Ninguna"),
        ("basica", "Básica"),
        ("intermedia", "Intermedia"),
        ("avanzada", "Avanzada"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    initial_balance = models.DecimalField(
        "Saldo inicial", max_digits=18, decimal_places=2, default=default_initial_balance
    )
    cash_balance = models.DecimalField(
        "Efectivo disponible", max_digits=18, decimal_places=2, default=default_initial_balance
    )
    risk_profile = models.CharField(
        "Perfil de riesgo", max_length=20, choices=RISK_CHOICES, default="moderado"
    )
    experience = models.CharField(
        "Experiencia", max_length=20, choices=EXPERIENCE_CHOICES, default="ninguna"
    )
    bio = models.CharField("Objetivo de inversión", max_length=240, blank=True)
    description = models.TextField("Descripción breve", max_length=400, blank=True)
    avatar = models.ImageField("Foto de perfil", upload_to="avatars/", null=True, blank=True)
    show_in_ranking = models.BooleanField("Aparecer en el ranking", default=True)
    # Autorización de tratamiento de datos (Ley 1581): fecha y versión aceptadas
    terms_accepted_at = models.DateTimeField("Aceptó los términos el", null=True, blank=True)
    terms_version = models.CharField("Versión de términos aceptada", max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

    def accept_terms(self):
        from django.utils import timezone

        self.terms_accepted_at = timezone.now()
        self.terms_version = settings.LEGAL["TERMS_VERSION"]
        self.save(update_fields=["terms_accepted_at", "terms_version", "updated_at"])

    @property
    def terms_current(self) -> bool:
        return bool(self.terms_accepted_at) and self.terms_version == settings.LEGAL["TERMS_VERSION"]

    def __str__(self):
        return f"Perfil de {self.user.username}"

    # Operaciones atómicas a nivel de base de datos: evitan sobrescribir el saldo
    # con una instancia desactualizada y previenen condiciones de carrera.
    def debit(self, amount: Decimal):
        updated = Profile.objects.filter(pk=self.pk, cash_balance__gte=amount).update(
            cash_balance=F("cash_balance") - amount, updated_at=timezone.now()
        )
        self.refresh_from_db(fields=["cash_balance"])
        if not updated:
            raise InsufficientFunds(
                f"Tu cuenta principal solo tiene {usd(self.cash_balance)} disponibles."
            )

    def credit(self, amount: Decimal):
        Profile.objects.filter(pk=self.pk).update(
            cash_balance=F("cash_balance") + amount, updated_at=timezone.now()
        )
        self.refresh_from_db(fields=["cash_balance"])
