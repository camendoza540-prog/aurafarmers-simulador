from django.conf import settings
from django.db import models
from django.db.models import Q


class FriendRequest(models.Model):
    """Solicitud de amistad. Al aceptarse, ambos usuarios pueden chatear."""

    STATUS_CHOICES = [("pending", "Pendiente"), ("accepted", "Aceptada"), ("rejected", "Rechazada")]

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_requests")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_requests")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["from_user", "to_user"], name="unique_friend_request"),
            models.CheckConstraint(condition=~Q(from_user=models.F("to_user")), name="no_self_request"),
        ]
        verbose_name = "Solicitud de amistad"
        verbose_name_plural = "Solicitudes de amistad"

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"


class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"

    def __str__(self):
        return f"{self.sender} → {self.recipient}: {self.body[:40]}"
