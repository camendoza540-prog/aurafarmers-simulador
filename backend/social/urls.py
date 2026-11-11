from django.urls import path

from . import views

urlpatterns = [
    path("summary/", views.summary, name="social_summary"),
    path("users/", views.search_users, name="social_search"),
    path("users/<int:user_id>/", views.user_detail, name="social_user"),
    path("requests/", views.requests_view, name="social_requests"),
    path("requests/<int:pk>/", views.cancel_request, name="social_cancel"),
    path("requests/<int:pk>/<str:action>/", views.respond_view, name="social_respond"),
    path("friends/", views.friends, name="social_friends"),
    path("friends/<int:user_id>/", views.unfriend, name="social_unfriend"),
    path("messages/<int:user_id>/", views.messages, name="social_messages"),
]
