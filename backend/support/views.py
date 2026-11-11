from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view, throttle_classes

from config.throttles import TicketThrottle
from rest_framework.response import Response

from .faq import FAQ, auto_reply
from .models import SupportMessage, SupportTicket


class NewTicketSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=120, min_length=4)
    category = serializers.ChoiceField(choices=SupportTicket.CATEGORY_CHOICES)
    body = serializers.CharField(max_length=4000, min_length=10)


def _author(m):
    if m.is_automatic:
        return {"name": "Asistente automático", "staff": True, "avatar_url": None}
    u = m.author
    if not u:
        return {"name": "Usuario eliminado", "staff": False, "avatar_url": None}
    name = (u.get_full_name() or u.username).strip()
    return {"name": f"{name} · Soporte" if m.from_staff else name, "staff": m.from_staff,
            "avatar_url": u.profile.avatar.url if hasattr(u, "profile") and u.profile.avatar else None}


def ticket_payload(t, with_messages=False):
    data = {
        "id": t.id, "subject": t.subject, "category": t.category, "category_label": t.get_category_display(),
        "status": t.status, "status_label": t.get_status_display(), "created_at": t.created_at,
        "updated_at": t.updated_at, "user_seen": t.user_seen,
        "user": {"id": t.user_id, "username": t.user.username, "name": (t.user.get_full_name() or t.user.username).strip()},
        "assigned_to": t.assigned_to.get_full_name() or t.assigned_to.username if t.assigned_to else None,
    }
    if with_messages:
        data["messages"] = [{"id": m.id, "body": m.body, "created_at": m.created_at, "author": _author(m)}
                            for m in t.messages.select_related("author__profile")]
    else:
        last = t.messages.order_by("-id").first()
        data["last_message"] = last.body[:140] if last else ""
    return data


def _visible(request):
    qs = SupportTicket.objects.select_related("user", "assigned_to")
    return qs if request.user.is_staff else qs.filter(user=request.user)


@api_view(["GET"])
def faq(request):
    return Response({"faq": FAQ, "categories": [{"value": v, "label": l} for v, l in SupportTicket.CATEGORY_CHOICES]})


@api_view(["GET", "POST"])
@throttle_classes([TicketThrottle])
def tickets(request):
    if request.method == "POST":
        s = NewTicketSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        with transaction.atomic():
            t = SupportTicket.objects.create(user=request.user, subject=s.validated_data["subject"],
                                             category=s.validated_data["category"])
            SupportMessage.objects.create(ticket=t, author=request.user, body=s.validated_data["body"])
            SupportMessage.objects.create(ticket=t, author=None, from_staff=True, is_automatic=True, body=auto_reply(t))
        return Response(ticket_payload(t, True), status=status.HTTP_201_CREATED)
    qs = _visible(request)
    st = request.query_params.get("status")
    if st:
        qs = qs.filter(status=st)
    return Response([ticket_payload(t) for t in qs[:200]])


@api_view(["GET"])
def ticket_detail(request, pk):
    t = get_object_or_404(_visible(request), pk=pk)
    if t.user_id == request.user.id and not t.user_seen:
        t.user_seen = True
        t.save(update_fields=["user_seen"])
    return Response(ticket_payload(t, True))


@api_view(["POST"])
def ticket_reply(request, pk):
    t = get_object_or_404(_visible(request), pk=pk)
    body = (request.data.get("body") or "").strip()
    if len(body) < 2:
        return Response({"detail": "Escribe un mensaje."}, status=status.HTTP_400_BAD_REQUEST)
    if t.status == "closed":
        return Response({"detail": "El ticket está cerrado. Abre uno nuevo si necesitas más ayuda."}, status=status.HTTP_400_BAD_REQUEST)
    staff_reply = request.user.is_staff and t.user_id != request.user.id
    SupportMessage.objects.create(ticket=t, author=request.user, from_staff=staff_reply, body=body[:4000])
    if staff_reply:
        t.status = "answered"
        t.user_seen = False
        if not t.assigned_to:
            t.assigned_to = request.user
    else:
        t.status = "open"
    t.save()
    return Response(ticket_payload(t, True), status=status.HTTP_201_CREATED)


@api_view(["POST"])
def ticket_close(request, pk):
    t = get_object_or_404(_visible(request), pk=pk)
    t.status = "closed"
    t.user_seen = True
    t.save()
    return Response(ticket_payload(t, True))
