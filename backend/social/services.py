"""Relaciones entre usuarios: amistad y mensajería directa."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import FriendRequest, Message

User = get_user_model()


class SocialError(Exception):
    pass


def friends_of(user):
    accepted = FriendRequest.objects.filter(Q(from_user=user) | Q(to_user=user), status="accepted")
    ids = {r.to_user_id if r.from_user_id == user.id else r.from_user_id for r in accepted}
    return User.objects.filter(id__in=ids).select_related("profile")


def are_friends(a, b) -> bool:
    return FriendRequest.objects.filter(
        Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a), status="accepted"
    ).exists()


def relationship(me, other) -> dict:
    """Estado de la relación vista desde «me»: none, friends, sent, received."""
    req = FriendRequest.objects.filter(Q(from_user=me, to_user=other) | Q(from_user=other, to_user=me)).exclude(status="rejected").first()
    if not req:
        return {"status": "none", "request_id": None}
    if req.status == "accepted":
        return {"status": "friends", "request_id": req.id}
    return {"status": "sent" if req.from_user_id == me.id else "received", "request_id": req.id}


def send_request(me, other) -> FriendRequest:
    if other == me:
        raise SocialError("No puedes enviarte una solicitud a ti mismo.")
    if other.is_staff:
        raise SocialError("Para hablar con el equipo de soporte usa la sección Soporte.")
    rel = relationship(me, other)
    if rel["status"] == "friends":
        raise SocialError("Ya son amigos.")
    if rel["status"] == "sent":
        raise SocialError("Ya enviaste una solicitud a este usuario.")
    if rel["status"] == "received":
        # Si el otro ya me había escrito, aceptar directamente
        req = FriendRequest.objects.get(pk=rel["request_id"])
        return respond(me, req, accept=True)
    req, _ = FriendRequest.objects.update_or_create(
        from_user=me, to_user=other, defaults={"status": "pending", "responded_at": None}
    )
    FriendRequest.objects.filter(from_user=other, to_user=me, status="rejected").delete()
    return req


def respond(me, req: FriendRequest, accept: bool) -> FriendRequest:
    if req.to_user_id != me.id or req.status != "pending":
        raise SocialError("Esta solicitud ya no está disponible.")
    req.status = "accepted" if accept else "rejected"
    req.responded_at = timezone.now()
    req.save(update_fields=["status", "responded_at"])
    return req


def remove_friend(me, other):
    FriendRequest.objects.filter(Q(from_user=me, to_user=other) | Q(from_user=other, to_user=me)).delete()


def send_message(me, other, body: str) -> Message:
    body = (body or "").strip()
    if not body:
        raise SocialError("Escribe un mensaje.")
    if len(body) > 2000:
        raise SocialError("El mensaje no puede superar 2.000 caracteres.")
    if not are_friends(me, other):
        raise SocialError("Solo puedes escribir a usuarios que aceptaron tu solicitud.")
    return Message.objects.create(sender=me, recipient=other, body=body)


def conversation(me, other, after_id: int | None = None, limit: int = 200):
    qs = Message.objects.filter(Q(sender=me, recipient=other) | Q(sender=other, recipient=me))
    if after_id:
        qs = qs.filter(id__gt=after_id)
        msgs = list(qs.order_by("id")[:limit])
    else:
        msgs = list(qs.order_by("-id")[:limit])[::-1]
    Message.objects.filter(sender=other, recipient=me, read_at=None).update(read_at=timezone.now())
    return msgs
