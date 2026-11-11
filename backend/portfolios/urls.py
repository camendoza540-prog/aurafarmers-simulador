from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register("portfolios", views.PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("transactions/", views.all_transactions, name="all_transactions"),
    path("trading/account/", views.trading_account, name="trading_account"),
    path("positions/", views.all_positions, name="all_positions"),
    path("positions/<int:pk>/", views.position_protection, name="position_protection"),
    path("positions/<int:pk>/close/", views.position_close, name="position_close"),
    path("", include(router.urls)),
]
