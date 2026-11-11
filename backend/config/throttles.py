"""Límites de peticiones por alcance (solo para acciones sensibles o de escritura)."""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class RegisterThrottle(AnonRateThrottle):
    scope = "register"


class PasswordThrottle(UserRateThrottle):
    scope = "password"


class _WriteOnly(UserRateThrottle):
    """Cuenta solo los envíos (POST); las lecturas periódicas del chat no se limitan."""

    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)


class MessageThrottle(_WriteOnly):
    scope = "messages"


class TicketThrottle(_WriteOnly):
    scope = "tickets"
