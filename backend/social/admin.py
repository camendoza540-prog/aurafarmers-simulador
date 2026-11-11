from django.contrib import admin

from .models import FriendRequest, Message


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at")
    list_filter = ("status",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "sender", "recipient", "body", "read_at")
    search_fields = ("sender__username", "recipient__username", "body")
