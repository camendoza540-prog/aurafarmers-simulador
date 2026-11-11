from django.contrib import admin

from .models import SavingsAccount


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "product", "rate_ea", "principal", "simulated_days", "status", "opened_at")
    list_filter = ("product", "status")
    search_fields = ("name", "user__username")
