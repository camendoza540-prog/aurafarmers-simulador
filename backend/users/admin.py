from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "cash_balance", "initial_balance", "risk_profile", "experience", "created_at")
    list_filter = ("risk_profile", "experience")
    search_fields = ("user__username", "user__email")
