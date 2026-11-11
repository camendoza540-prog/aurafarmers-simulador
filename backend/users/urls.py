from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.ThrottledTokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", views.me, name="me"),
    path("change-password/", views.change_password, name="change_password"),
    path("reset/", views.reset, name="reset_simulation"),
    path("avatar/", views.avatar, name="avatar"),
    path("ranking/", views.leaderboard, name="ranking"),
    path("accept-terms/", views.accept_terms, name="accept_terms"),
    path("delete-account/", views.delete_account, name="delete_account"),
]
