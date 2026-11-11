from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    CATEGORY_CHOICES = [
        ("cuenta", "Cuenta y perfil"),
        ("operaciones", "Compras, ventas y CFD"),
        ("ahorro", "Ahorro y CDT"),
        ("escenarios", "Simulación de escenarios"),
        ("aprendizaje", "Lecciones y conceptos"),
        ("error", "Reportar un error"),
        ("otro", "Otro"),
    ]
    STATUS_CHOICES = [("open", "Esperando respuesta"), ("answered", "Respondido"), ("closed", "Cerrado")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField("Asunto", max_length=120)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default="otro")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open", db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="assigned_tickets", limit_choices_to={"is_staff": True})
    user_seen = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Ticket de soporte"
        verbose_name_plural = "Tickets de soporte"

    def __str__(self):
        return f"#{self.pk} {self.subject}"


class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    from_staff = models.BooleanField(default=False)
    is_automatic = models.BooleanField(default=False)
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "Mensaje de soporte"
        verbose_name_plural = "Mensajes de soporte"
