from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes

from config.throttles import MessageThrottle
from rest_framework.response import Response

from .models import FriendRequest, Message
from .services import (
    SocialError, conversation, friends_of, relationship, remove_friend, respond, send_message, send_request,
)

User = get_user_model()


def _err(e):
    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def user_card(u, me=None):
    from users.services import net_worth

    p = u.profile
    card = {
        "id": u.id, "username": u.username, "name": (u.get_full_name() or u.username).strip(),
        "avatar_url": p.avatar.url if p.avatar else None, "description": p.description,
        "risk_profile": p.get_risk_profile_display(),
    }
    if me is not None:
        card["relationship"] = relationship(me, u)
        if p.show_in_ranking:
            card["gain_pct"] = net_worth(u)["gain_pct"]
    return card


def message_payload(m, me):
    return {"id": m.id, "body": m.body, "mine": m.sender_id == me.id, "created_at": m.created_at, "read": m.read_at is not None}


@api_view(["GET"])
def search_users(request):
    q = (request.query_params.get("q") or "").strip()
    if len(q) < 2:
        return Response([])
    qs = (User.objects.filter(is_active=True, is_staff=False, is_superuser=False)
          .exclude(pk=request.user.pk)
          .filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
          .select_related("profile")[:20])
    return Response([user_card(u, request.user) for u in qs])


@api_view(["GET"])
def user_detail(request, user_id):
    u = get_object_or_404(User.objects.select_related("profile"), pk=user_id, is_active=True)
    return Response(user_card(u, request.user))


@api_view(["GET", "POST"])
def requests_view(request):
    me = request.user
    if request.method == "POST":
        other = get_object_or_404(User, pk=request.data.get("to_user"), is_active=True)
        try:
            req = send_request(me, other)
        except SocialError as e:
            return _err(e)
        msg = "Ahora son amigos." if req.status == "accepted" else f"Solicitud enviada a {other.username}."
        return Response({"detail": msg, "status": req.status}, status=status.HTTP_201_CREATED)
    incoming = FriendRequest.objects.filter(to_user=me, status="pending").select_related("from_user__profile")
    outgoing = FriendRequest.objects.filter(from_user=me, status="pending").select_related("to_user__profile")
    return Response({
        "incoming": [{"id": r.id, "created_at": r.created_at, "user": user_card(r.from_user)} for r in incoming],
        "outgoing": [{"id": r.id, "created_at": r.created_at, "user": user_card(r.to_user)} for r in outgoing],
    })


@api_view(["POST"])
def respond_view(request, pk, action):
    if action not in ("accept", "reject"):
        return Response(status=status.HTTP_404_NOT_FOUND)
    req = get_object_or_404(FriendRequest, pk=pk)
    try:
        respond(request.user, req, accept=(action == "accept"))
    except SocialError as e:
        return _err(e)
    return Response({"detail": "Solicitud aceptada." if action == "accept" else "Solicitud rechazada."})


@api_view(["DELETE"])
def cancel_request(request, pk):
    get_object_or_404(FriendRequest, pk=pk, from_user=request.user, status="pending").delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def friends(request):
    me = request.user
    out = []
    for f in friends_of(me):
        last = Message.objects.filter(Q(sender=me, recipient=f) | Q(sender=f, recipient=me)).order_by("-id").first()
        unread = Message.objects.filter(sender=f, recipient=me, read_at=None).count()
        card = user_card(f)
        card.update({
            "last_message": message_payload(last, me) if last else None,
            "unread": unread,
        })
        out.append(card)
    out.sort(key=lambda c: (c["last_message"] or {}).get("id", 0), reverse=True)
    return Response(out)


@api_view(["DELETE"])
def unfriend(request, user_id):
    other = get_object_or_404(User, pk=user_id)
    remove_friend(request.user, other)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@throttle_classes([MessageThrottle])
def messages(request, user_id):
    me = request.user
    other = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    if request.method == "POST":
        try:
            m = send_message(me, other, request.data.get("body"))
        except SocialError as e:
            return _err(e)
        return Response(message_payload(m, me), status=status.HTTP_201_CREATED)
    try:
        after = int(request.query_params.get("after") or 0) or None
    except ValueError:
        after = None
    msgs = conversation(me, other, after)
    return Response({"user": user_card(other, me), "messages": [message_payload(m, me) for m in msgs]})


@api_view(["GET"])
def summary(request):
    """Contadores para las insignias del menú (se consulta cada pocos segundos)."""
    from support.models import SupportTicket

    me = request.user
    data = {
        "unread_messages": Message.objects.filter(recipient=me, read_at=None).count(),
        "pending_requests": FriendRequest.objects.filter(to_user=me, status="pending").count(),
        "support_unread": SupportTicket.objects.filter(user=me, status="answered", user_seen=False).count(),
    }
    if me.is_staff:
        data["support_open"] = SupportTicket.objects.filter(status="open").count()
    return Response(data)
