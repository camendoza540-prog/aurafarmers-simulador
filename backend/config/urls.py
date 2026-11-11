from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(request):
    return JsonResponse({
        "nombre": "Plataforma de Simulación de Inversión — Aura Farmers",
        "endpoints": {
            "auth": "/api/auth/",
            "mercado": "/api/market/",
            "portafolios": "/api/portfolios/",
            "resumen": "/api/dashboard/",
            "ahorro": "/api/savings/",
            "escenarios": "/api/scenarios/",
            "aprendizaje": "/api/learning/",
            "comunidad": "/api/social/",
            "soporte": "/api/support/",
            "admin": "/admin/",
        },
    })


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api_root),
    path("api/auth/", include("users.urls")),
    path("api/market/", include("market.urls")),
    path("api/", include("portfolios.urls")),
    path("api/savings/", include("savings.urls")),
    path("api/scenarios/", include("scenarios.urls")),
    path("api/learning/", include("learning.urls")),
    path("api/social/", include("social.urls")),
    path("api/support/", include("support.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Aura Farmers · Administración"
admin.site.site_title = "Simulador de Inversión"
admin.site.index_title = "Panel de administración"
