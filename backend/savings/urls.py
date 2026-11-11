from django.urls import path

from . import views

urlpatterns = [
    path("products/", views.products, name="savings_products"),
    path("accounts/", views.accounts, name="savings_accounts"),
    path("accounts/<int:pk>/advance/", views.advance, name="savings_advance"),
    path("accounts/<int:pk>/deposit/", views.deposit, name="savings_deposit"),
    path("accounts/<int:pk>/withdraw/", views.withdraw, name="savings_withdraw"),
    path("accounts/<int:pk>/renew/", views.renew, name="savings_renew"),
    path("calculator/", views.calc, name="savings_calculator"),
]
