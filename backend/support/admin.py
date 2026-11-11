from django.contrib import admin

from .models import SupportMessage, SupportTicket


class MessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1
    fields = ("author", "from_staff", "body", "created_at")
    readonly_fields = ("created_at",)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "user", "category", "status", "assigned_to", "updated_at")
    list_filter = ("status", "category")
    search_fields = ("subject", "user__username")
    inlines = [MessageInline]
