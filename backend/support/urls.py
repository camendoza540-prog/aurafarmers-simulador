from django.urls import path

from . import views

urlpatterns = [
    path("faq/", views.faq, name="support_faq"),
    path("tickets/", views.tickets, name="support_tickets"),
    path("tickets/<int:pk>/", views.ticket_detail, name="support_ticket"),
    path("tickets/<int:pk>/messages/", views.ticket_reply, name="support_reply"),
    path("tickets/<int:pk>/close/", views.ticket_close, name="support_close"),
]
