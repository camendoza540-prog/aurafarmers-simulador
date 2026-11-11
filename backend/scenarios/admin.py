from django.contrib import admin

from .models import ScenarioRun


@admin.register(ScenarioRun)
class ScenarioRunAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "portfolio_name", "preset")
    list_filter = ("preset",)
    readonly_fields = ("params", "summary")
