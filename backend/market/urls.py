from django.urls import path

from . import views

urlpatterns = [
    path("instruments/", views.instrument_list, name="instrument_list"),
    path("quotes/", views.quotes, name="quotes"),
    path("overview/", views.overview, name="market_overview"),
    path("news/", views.market_news, name="market_news"),
    path("instruments/<str:symbol>/", views.instrument_detail, name="instrument_detail"),
    path("instruments/<str:symbol>/history/", views.instrument_history, name="instrument_history"),
    path("instruments/<str:symbol>/candles/", views.instrument_candles, name="instrument_candles"),
    path("instruments/<str:symbol>/news/", views.instrument_news, name="instrument_news"),
]
